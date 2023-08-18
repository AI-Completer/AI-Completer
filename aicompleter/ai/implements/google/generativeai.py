import copy
from typing import Any, AsyncGenerator, Optional
import uuid

import aiohttp

from aicompleter.ai.ai import Conversation, Message

from ....config import Config, ConfigModel
from ....utils import asdict
from ...ai import AuthorType, ChatTransformer, Conversation, Message, TextTransformer
from ...token import Encoder
from ... import ai

class ChatOptions(ConfigModel):
    temperature: Optional[float] = None
    topP: Optional[float] = None
    topK: Optional[int] = None

class TextOptions(ChatOptions):
    """Optians for plam"""
    # candidate_count: Optional[int] = None           # default: 1, it's part of the options, but we don't want to expose it
    maxOutputTokens: Optional[int] = None
    stopSequences: Optional[list[str]] = None      # for example: ["<|END|>"]
    safetySettings: Optional[list[dict[str, Any]]] = None
    # for example: [{"category":"HARM_CATEGORY_DEROGATORY","threshold":3},{"category":"HARM_CATEGORY_TOXICITY","threshold":2},{"category":"HARM_CATEGORY_VIOLENCE","threshold":2},{"category":"HARM_CATEGORY_SEXUAL","threshold":2},{"category":"HARM_CATEGORY_MEDICAL","threshold":2},{"category":"HARM_CATEGORY_DANGEROUS","threshold":2}]

class GenerativeTextConfig(ConfigModel):
    """Config for plam"""
    options: TextOptions = TextOptions()
    proxy: Optional[str] = None

class GenerativeChatConfig(ConfigModel):
    """Config for plam"""
    options: ChatOptions = ChatOptions()
    proxy: Optional[str] = None

class Chater(ChatTransformer):
    '''
    Chater using plam
    '''
    def __init__(self, config: Config):
        self.update_config(config)

    def new_conversation(self, user: str | None = None, id: uuid.UUID | None = None, init_prompt: str | None = None, examples:Optional[list[Message]] = None) -> Conversation:
        ret = Conversation(user=user, id=id or uuid.uuid4())
        if init_prompt:
            ret.messages.append(Message(content=init_prompt, role=AuthorType.BASE))
        if examples:
            ret.data['examples'] = examples
        return ret

    def update_config(self, config: Config):
        self.config = GenerativeChatConfig(config)
        self.model = config.get('model', 'chat-bison-001')
        self.api_url = config.get('api-url', "https://generativelanguage.googleapis.com/v1beta2/models/")
        self.api_key = config.require('api-key')

    def check_conversation(self, conversation: Conversation) -> bool:
        '''
        Check if the conversation is in proper format

        This check is for the plam model, which limit the conversation strictly
        '''
        # Only one system prompt
        index = 0
        if conversation.messages[0].role in {AuthorType.BASE, AuthorType.SYSTEM}:
            index = 1
        excepted_role = 'user'
        while index < len(conversation.messages):
            if conversation.messages[index].role != excepted_role:
                return False
            excepted_role = 'user' if excepted_role == 'assistant' else 'assistant'
            index += 1
        if excepted_role != 'assistant':
            return False
        return True
    
    @staticmethod
    def _generate_format(conversation: Conversation) -> dict:
        '''
        Generate the format for palm
        '''
        context = ''
        messages = []
        baseindex =0
        examples = conversation.data.get('examples', None)
        if conversation.messages[0].author in {AuthorType.BASE, AuthorType.SYSTEM}:
            context = conversation.messages[0].content
            baseindex = 1
        for message in conversation.messages[baseindex:]:
            messages.append({
                "content": message.content,
            })
        ret = {
            'context': context,
            'messages': messages
        }
        if examples:
            examples_list = []
            if len(examples) % 2 != 0:
                raise ValueError('Examples must be even')
            for userword, assistantword in zip(examples[::2], examples[1::2]):
                examples_list.append({
                    'input':{'content': userword.content},
                    'output':{'content': assistantword.content}
                })
            ret['examples'] = examples_list
        return ret

    async def generate(self, conversation: Conversation) -> AsyncGenerator[Message, None]:
        '''
        Generate the message

        Parameters:
        ----------
        conversation: Conversation, the conversation to generate
        examples: Optional[list[Message]], the examples

        Returns:
        --------
        AsyncGenerator[Message, None], the generated message, due to the API limit, the message will be yield for only one time.
        '''
        if not self.check_conversation(conversation):
            raise ValueError('Conversation is not in proper format')
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.api_url}{self.model}:generateMessage?key={self.api_key}', json={
                "prompt":self._generate_format(conversation),
                **asdict(self.config.options, filter=lambda k, v: v is not None and k != 'candidate_count')
            }, proxy = self.config.proxy) as response:
                data = await response.json()
                if 'candidates' not in data:
                    # The message is banned by some reason
                    from ....error import AIGenerateError
                    raise AIGenerateError('', data=data)
                candidate = data['candidates'][0]
                yield Message(content=candidate['content'], role='assistant', data=data)

    async def generate_many(self, conversation: Conversation, num:int) -> AsyncGenerator[list[Message], None]:
        '''
        Generate the messages

        Parameters:
        ----------
        conversation: Conversation, the conversation to generate
        examples: Optional[list[Message]], the examples
        num: int, the number of messages to generate

        Returns:
        --------
        AsyncGenerator[list[Message], None], the generated messages, due to the API limit, the messages will be yield for only one time.
        '''
        if not self.check_conversation(conversation):
            raise ValueError('Conversation is not in proper format')
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.api_url}{self.model}:generateMessage?key={self.api_key}', json={
                "prompt":self._generate_format(conversation),
                "candidate_count":num,
                **asdict(self.config.options, filter=lambda k, v: v is not None and k != 'candidate_count'),
            }, proxy = self.config.proxy) as response:
                data = await response.json()
                if 'candidates' not in data:
                    # The message is banned by some reason
                    from ....error import AIGenerateError
                    raise AIGenerateError('', data=data)
                candidates = data['candidates']
                ret = []
                for candidate in candidates:
                    ret.append(Message(content=candidate['content'], role='assistant', data=data))
                yield ret

    def limit_token(self, history:Conversation, max_token:int = 2048, ignore_init_prompt:bool = True):
        '''
        Limit the tokens
        :param history: The history
        :param max_token: The max token
        :param ignore_init_prompt: Ignore the init prompt
        '''
        if len(history.messages) == 0:
            return history
        if len(history.messages) == 1 and ignore_init_prompt:
            return history
        encoder = Encoder(model = self.model)
        totallen = sum(encoder.getTokenLength(message.content) for message in history.messages)
        init_len = encoder.getTokenLength(history.messages[0].content)
        if totallen <= max_token:
            return history
        if ignore_init_prompt:
            if totallen - init_len <= max_token:
                return history
        # Cut needed
        new_his = copy.deepcopy(history)
        for index in range(len(new_his.messages)):
            totallen -= encoder.getTokenLength(new_his.messages[index].content)
            if ignore_init_prompt and index == 0:
                continue
            if totallen <= max_token:
                break
        
        add_msg = None
        for rv in range(index, -1, -1):
            if ignore_init_prompt and rv == 0:
                continue
            add_msg = new_his.messages[rv]
            break

        add_msg.content = encoder.decode(encoder.encode(add_msg.content)[totallen-max_token:])
        ret_messages = []
        for i, message in enumerate(new_his.messages):
            if ignore_init_prompt and i == 0:
                ret_messages.append(message)
                continue
            if i == rv:
                ret_messages.append(add_msg)
                continue
            if i < index:
                continue
            ret_messages.append(message)
        new_his.messages = ret_messages
        return new_his

class TextCompleter(TextTransformer):
    '''
    Text completer using plam
    '''
    def __init__(self, config: Config):
        self.update_config(config)

    def update_config(self, config: Config):
        self.config = GenerativeTextConfig(config)
        self.model = config.get('model', 'text-bison-001')
        self.api_url = config.get('api-url', "https://generativelanguage.googleapis.com/v1beta2/models/")
        self.api_key = config.require('api-key')

    def set_stopwords(self, stopwords: list[str]):
        '''
        Set the stopwords

        Parameters:
        ----------
        stopwords: list[str], the stopwords
        '''
        self.config.options.stopSequences = stopwords

    async def generate(self, text: str) -> AsyncGenerator[Message, None]:
        '''
        Complete the text

        Parameters:
        ----------
        text: str, the text to complete

        Returns:
        --------
        AsyncGenerator[Message, None], the completed Message, due to the API limit, the message will be yield for only one time.
        '''
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.api_url}{self.model}:generateText?key={self.api_key}', json={
                "prompt": {
                    "text": text
                },
                **asdict(self.config.options, filter=lambda k, v: v is not None)
            }, proxy = self.config.proxy) as response:
                response.raise_for_status()
                data = await response.json()
                if 'candidates' not in data:
                    # The message is banned by some reason
                    from ....error import AIGenerateError
                    raise AIGenerateError('', data=data)
                candidate = data['candidates'][0]
                yield Message(content=candidate['output'], data=data)

    async def generate_many(self, prompt: str, num: int) -> AsyncGenerator[list[Message], None]:
        '''
        Complete the text

        Parameters:
        ----------
        text: str, the text to complete
        num: int, the number of text to generate

        Returns:
        --------
        AsyncGenerator[list[Message], None], the completed Messages, due to the API limit, the messages will be yield for only one time.
        '''
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.api_url}{self.model}:generateText?key={self.api_key}', json={
                "prompt": prompt,
                "candidate_count":num,
                **asdict(self.config.options, filter=lambda k, v: v is not None and k != 'candidate_count'),
            }, proxy = self.config.proxy) as response:
                response.raise_for_status()
                data = await response.json()
                candidates = data['candidates']
                if 'candidates' not in data:
                    # The message is banned by some reason
                    from ....error import AIGenerateError
                    raise AIGenerateError('', data=data)
                ret = []
                for candidate in candidates:
                    ret.append(Message(content=candidate['output'], data=data))
                yield ret

class Embedder(ai.Embedder):
    def __init__(self, config: Config):
        self.update_config(config)

    def update_config(self, config: Config):
        self.model = config.get('model', 'embedding-gecko-001')
        self.api_key = config.require('api-key')
        self.proxy = config.get('proxy', None)

    async def generate(self, prompt: str) -> AsyncGenerator[list[float], None]:
        '''
        Generate the embedding

        Parameters:
        ----------
        prompt: str, the prompt

        Returns:
        --------
        AsyncGenerator[list[float], None], the embedding, due to the API limit, the embedding will be yield for only one time.
        '''
        async with aiohttp.ClientSession() as session:
            async with session.post(f'https://generativelanguage.googleapis.com/v1beta2/models/{self.model}:embedText?key={self.api_key}', json={
                "text": prompt,
            }, proxy = self.proxy) as response:
                response.raise_for_status()
                data = await response.json()
                yield data['embedding']['value']

class GooglePaLMAPI:
    '''
    This is a low level API caller for Google PaLM, no return value is processed
    '''
    def __init__(self, api_key:str, api_url:str = 'https://generativelanguage.googleapis.com/v1beta2/', **kwargs):
        self.api_key = api_key
        self.api_url = api_url
        self.options = kwargs

    async def _request(self, url:str, data:Optional[dict] = None):
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, **self.options) as response:
                response.raise_for_status()
                return await response.json()

    def generateText(self, model:str, data:dict):
        return self._request(f'{self.api_url}models/{model}:generateText?key={self.api_key}', data)
            
    def generateMessage(self, model:str, data:dict):
        return self._request(f'{self.api_url}models/{model}:generateMessage?key={self.api_key}', data)
            
    def embedText(self, model:str, data:dict):
        return self._request(f'{self.api_url}models/{model}:embedText?key={self.api_key}', data)
    
    def countMessageTokens(self, model:str, data:dict):
        return self._request(f'{self.api_url}models/{model}:countMessageTokens?key={self.api_key}', data)

    def getModel(self, model:str):
        return self._request(f'{self.api_url}models/{model}?key={self.api_key}')
    
    def listModels(self):
        return self._request(f'{self.api_url}models?key={self.api_key}')
