import copy
from enum import auto
import json
from tkinter.filedialog import Open
from typing import Any, Generator, Iterator, Literal, Optional, Self
import uuid

import aiohttp
import attr

from aicompleter import utils
from aicompleter.ai import *
from aicompleter.ai.ai import Conversation
from aicompleter.config import Config, EnhancedDict
from aicompleter.ai.token import Encoder

DEFAULT_API_URL:str = 'https://api.openai.com/v1/'
'BASE URL of OpenAI API'

@attr.s(auto_attribs=True)
class OpenAIConversation(Conversation):
    '''
    OpenAI Conversation
    '''
    function_call: Literal['none', 'auto'] | dict | None = attr.ib(default=None, validator=attr.validators.in_(['none', 'auto', None, dict]))
    'Function call mode of conversation'

    def generate_json(self) -> dict[str, Any]:
        ret = {}
        ret['user'] = self.user
        ret['messages'] = []
        for message in self.messages:
            if message.data:
                ret['messages'].append(mes_ret)
            else:
                mes_ret = {
                    'content': message.content,
                    'role': message.role,
                }
                if message.user:
                    mes_ret['name'] = message.user
                ret['messages'].append(mes_ret)
        if self.functions:
            functions_ret = []
            for function in self.functions:
                fun_ret = {}
                fun_ret['name'] = function.name
                fun_ret['params'] = []
                required_params = []
                if function.description:
                    fun_ret['description'] = function.description
                for param in function.parameters:
                    param_ret = {}
                    param_ret['name'] = param.name
                    if param.type:
                        param_ret['type'] = param.type
                    if param.required:
                        required_params.append(param.name)
                    if param.description:
                        param_ret['description'] = param.description
                    if param.enum:
                        param_ret['enum'] = param.enum
                    fun_ret['params'].append(param_ret)
                if required_params:
                    fun_ret['required'] = required_params
                functions_ret.append(fun_ret)
            if functions_ret:
                ret['functions'] = functions_ret
        if self.function_call:
            ret['function_call'] = self.function_call
        return ret
    
    @staticmethod
    def from_conversation(conversation:Conversation) -> Self:
        '''
        Convert a conversation to OpenAIConversation
        '''
        ret = OpenAIConversation.__new__(OpenAIConversation)
        ret.__init__(**conversation.__dict__)
        return ret

class OpenAIGPT(Transformer):
    '''
    OpenAI GPT
    '''
    @property
    def stream(self) -> bool:
        '''
        Is stream
        '''
        return bool(self.config['chat'].get('stream', False))

    @stream.setter
    def stream(self, value:bool):
        '''
        Set stream
        '''
        self.config['chat']['stream'] = bool(value)

class Chater(ChatTransformer,OpenAIGPT):
    '''
    Chater
    '''
    REQUIRE_PARAMS:set[str] = {
        'max_tokens',
        'temperature',
        'top_p',
        'stream',
        'frequency_penalty',
        'presence_penalty',
        'stop',
        'n',
        'logit_bias',
        'user',
    }
    def __init__(self, config:Config, model:str = 'gpt-3.5-turbo'):
        super().__init__(
            name=model,
            support={"text"},
            config=config,
        )
        if not isinstance(self.config['chat'], EnhancedDict):
            raise ValueError(f'Invalid config: {self.config}')
        if not set(self.config['chat'].keys()) <= self.REQUIRE_PARAMS:
            raise ValueError(f'Unknown parameters: {set(config.keys()) - self.REQUIRE_PARAMS}')
        self.update_config(config)

    def new_conversation(self, user: str | None = None, id: uuid.UUID | None = None, init_prompt: str | None = None) -> OpenAIConversation:
        '''
        Create a new conversation
        '''
        return OpenAIConversation(
            user=user,
            id=id or uuid.uuid4(),
            messages=[Message(
                content = init_prompt,
                role = 'system'
            )] if init_prompt else [],
        )

    def update_config(self, config:Config):
        '''
        Update the config
        '''
        self.config = config
        self.api_key:str = self.config.require('openai.api-key')
        self.proxy:Optional[str] = self.config.get('proxy', None)
        self.api_url = self.config.get('openai.api-url', DEFAULT_API_URL)
        self.location = self.api_url + 'chat/completions'
        self.config.setdefault('sys.max_token', 2048)
    
    async def _request(self, conversation: Conversation) -> Generator[str, Any, None]:
        '''
        Request the conversation
        '''
        utils.typecheck(conversation, Conversation)
        # Convert to OoenAIConversation
        if not isinstance(conversation, OpenAIConversation):
            conversation = OpenAIConversation.from_conversation(conversation)

        async with aiohttp.ClientSession() as session:

            async with session.post(
                url=self.location,
                json=dict(
                    **conversation.generate_json(),
                    **self.config['chat'],
                    model = self.name,
                ),
                proxy=self.proxy if self.proxy else None,
                headers={
                    'Authorization': f'Bearer {self.api_key}'
                }
            ) as res:
                if res.status != 200:
                    raise RuntimeError(f'Error: {res.status} {res.reason}: ' + await res.text())
                async for value in res.content:
                    yield value.decode()

    async def generate_raw(self, conversation: Conversation) -> str:
        '''
        Generate the conversation and return raw bytes
        '''
        return ''.join([value async for value in self._request(conversation)])
    
    async def generate(self, conversation: Conversation) -> Generator[Message, Any, None]:
        '''
        Generate the conversation and return text
        '''
        full_text = ''
        async for value in self._request(conversation):
            full_text += value
            if '\n' in full_text:
                lines = full_text.splitlines()
                for line in lines[:-1]:
                    if line == 'data:[DONE]':
                        break
                    raw = json.loads(line)['choices'][0]['message']
                    ret_message = Message(
                        content = raw.get('content', ''),
                        role = raw['role'],
                        user = raw.get('name', None),
                        data = raw,
                    )
                    if 'function_call' in raw:
                        # Function call will be interpreted in the agent calss
                        ret_message.function_call = raw['function_call']
                    yield ret_message

                full_text = lines[-1]
        # Last line
        if full_text:
            raw = json.loads(full_text)['choices'][0]['message']
            ret_message = Message(
                content = raw.get('content', ''),
                role = raw['role'],
                user = raw.get('name', None),
                data = raw,
            )
            if 'function_call' in raw:
                # Function call will be interpreted in the agent calss
                ret_message.function_call = raw['function_call']
            yield ret_message

    async def generate_many(self, conversation: Conversation) -> Generator[list[Message], Any, None]:
        '''
        Generate the conversations and return text
        '''
        def _from_message(raw:dict, i:int) -> Message:
            '''
            Convert the raw message to Message
            '''
            raw = raw['choices'][i]['message']
            ret_message = Message(
                content = raw['content'],
                role = raw['role'],
                user = raw['name'] if 'name' in raw else None,
                data = raw,
            )
            if 'function_call' in raw:
                # Function call will be interpreted in the agent calss
                ret_message.function_call = raw['function_call']
            return ret_message
        full_text = ''
        async for value in self.generate(conversation):
            full_text += value
            if '\n' in full_text:
                lines = full_text.splitlines(keepends=True)
                for line in lines[:-1]:
                    yield [
                        _from_message(json.loads(line), i)
                        for i in range(len(json.loads(line)['choices']))
                        ]
                full_text = lines[-1]
        # Last line
        if full_text:
            yield [
                _from_message(json.loads(full_text), i)
                for i in range(len(json.loads(full_text)['choices']))
                ]
    
    async def update_conversation(self, history:Conversation, message: Message) -> Conversation:
        '''
        Ask the message
        '''
        new_his = history
        new_his.messages.append(message)
        new_his = self.limit_token(new_his, self.config['sys.max_token'])
        ret = await self.generate_text(new_his)
        new_his.messages.append(Message(
            content=ret,
            role='assistant',
        ))
        return new_his
    
    def limit_token(self, history:Conversation, max_token:int = 2048, ignore_system:bool = True):
        '''
        Limit the tokens
        :param history: The history
        :param max_token: The max token
        :param ignore_system: Whether to ignore system message, this flag will ignore its length and will forbid to cut the system message
        '''
        if len(history.messages) == 0:
            return history
        encoder = Encoder(model = self.name)
        totallen = sum(encoder.getTokenLength(message.content) for message in history.messages)
        systemlen = sum(encoder.getTokenLength(message.content) for message in history.messages if message.role == 'system')
        if totallen <= max_token:
            return history
        if ignore_system:
            if totallen - systemlen <= max_token:
                return history
        # Cut needed
        new_his = copy.deepcopy(history)
        for index in range(len(new_his.messages)):
            totallen -= encoder.getTokenLength(new_his.messages[index].content)
            if ignore_system and new_his.messages[index].role == 'system':
                continue
            if totallen <= max_token:
                break
        add_msg = None
        for rv in range(index, -1, -1):
            if ignore_system and new_his.messages[rv].role == 'system':
                continue
            add_msg = new_his.messages[rv]
            break
        add_msg.content = encoder.decode(encoder.encode(add_msg.content)[totallen-max_token:])
        ret_messages = []
        for i, message in enumerate(new_his.messages):
            if ignore_system and message.role == 'system':
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
    
class Completer(TextTransformer,OpenAIGPT):
    '''
    Completer
    '''
    REQUIRE_PARAMS:set[str] = {
        'max_tokens',
        'temperature',
        'top_p',
        'stream',
        'frequency_penalty',
        'presence_penalty',
        'stop',
        'n',
        'logit_bias',
        'user',

        'suffix',
        'logprobs',
        'echo',
        'best_of',
    }
    
    def __init__(self, model:str, config:Config):
        super().__init__(
            name=model,
            support={"text"},
            config=config,
        )
        if not isinstance(self.config['chat'], EnhancedDict):
            raise ValueError(f'Invalid config: {self.config}')
        if not set(self.config['chat'].keys()) <= self.REQUIRE_PARAMS:
            raise ValueError(f'Unknown parameters: {set(config.keys()) - self.REQUIRE_PARAMS}')
        self.update_config(config)

    def update_config(self, config:Config):
        '''
        Update the config
        '''
        self.config = config
        self.api_key:str = self.config.require('openai.api-key')
        self.proxy:Optional[str] = self.config.get('proxy', None)
        self.api_url = self.config.get('openai.api-url', DEFAULT_API_URL)
        self.location = self.api_url + 'completions'
        self.config.setdefault('sys.max_token', 2048)

    async def _request(self, prompt: str) -> Generator[str, Any, None]:
        '''
        Generate the prompt
        '''
        utils.typecheck(prompt, str)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.location,
                json=dict(
                    prompt=prompt,
                    **self.config['chat'],
                    model = self.name,
                ),
                proxy=self.proxy if self.proxy else None,
                headers={
                    'Authorization': f'Bearer {self.api_key}'
                }
            ) as res:
                if res.status != 200:
                    raise RuntimeError(f'Error: {res.status} {res.reason}')
                async for value in res.content:
                    yield value.decode()

    async def generate_raw(self, prompt: str) -> str:
        '''
        Generate the prompt and return raw bytes
        '''
        return ''.join([value async for value in self._request(prompt)])

    async def generate(self, prompt: str) -> Generator[str, Any, None]:
        '''
        Generate the prompt and return text
        '''
        full_text = ''
        async for value in self._request(prompt):
            full_text += value
            if '\n' in full_text:
                lines = full_text.split('\n')
                for line in lines[:-1]:
                    yield json.loads(line)['choices'][0]['text']
                full_text = lines[-1]

    async def generate_many(self, prompt: str) -> Generator[list[str], Any, None]:
        '''
        Generate the prompt and return text
        '''
        full_text = ''
        async for value in self.generate(prompt):
            full_text += value
            if '\n' in full_text:
                lines = full_text.splitlines(keepends=True)
                for line in lines[:-1]:
                    yield [
                        json.loads(line)['choices'][i]['text']
                        for i in range(len(json.loads(line)['choices']))
                        ]
                full_text = lines[-1]
