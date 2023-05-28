import json
from typing import Any, Generator, Iterator, Optional

import aiohttp
import attr

from aicompleter import utils
from aicompleter.ai import *
from aicompleter.ai.ai import Conversation, Message
from aicompleter.config import Config, EnhancedDict

BASE_URL:str = 'https://api.openai.com/v1/'
'BASE URL of OpenAI API'
COMPLETIONS_URL:str = f'{BASE_URL}completions'
'URL of OpenAI API completions'
CHAT_URL:str = f'{BASE_URL}chat/completions'
'URL of OpenAI API chat completions'

class OpenAIGPT(ai.ChatGPT):
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

class Chater(OpenAIGPT):
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
    def __init__(self, model:str, config:Config):
        super().__init__(
            name=model,
            support={"text"},
            location=CHAT_URL,
            config=config,
        )
        if not isinstance(self.config['chat'], EnhancedDict):
            raise ValueError(f'Invalid config: {self.config}')
        if not set(self.config['chat'].keys()) <= self.REQUIRE_PARAMS:
            raise ValueError(f'Unknown parameters: {set(config.keys()) - self.REQUIRE_PARAMS}')
        self.proxy:Optional[str] = self.config.get('proxy', None)
        self.api_key:str = self.config.require('openai.api-key')

    @property
    def stream(self):
        '''
        Is stream mode
        '''
        return self.config['chat'].get('stream', False)
    
    async def _request(self, conversation: Conversation) -> Generator[str, Any, None]:
        '''
        Request the conversation
        '''
        utils.typecheck(conversation, Conversation)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.location,
                json=dict(
                    messages =[
                        attr.asdict(message,
                                    filter=lambda atr,value:value != None and atr.name in {"role","content","user"}
                                    )
                                    for message in conversation.messages
                    ],
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

    async def generate_raw(self, conversation: Conversation) -> str:
        '''
        Generate the conversation and return raw bytes
        '''
        return ''.join([value async for value in self._request(conversation)])
    
    async def generate(self, conversation: Conversation) -> Generator[str, Any, None]:
        '''
        Generate the conversation and return text
        '''
        full_text = ''
        async for value in self._request(conversation):
            full_text += value
            if '\n' in full_text:
                lines = full_text.split('\n')
                for line in lines[:-1]:
                    yield json.loads(line)['choices'][0]['message']['content']
                full_text = lines[-1]

    async def generate_many(self, conversation: Conversation) -> Generator[list[str], Any, None]:
        '''
        Generate the conversations and return text
        '''
        full_text = ''
        async for value in self.generate(conversation):
            full_text += value
            if '\n' in full_text:
                lines = full_text.splitlines(keepends=True)
                for line in lines[:-1]:
                    yield [
                        json.loads(line)['choices'][i]['message']['content']
                        for i in range(len(json.loads(line)['choices']))
                        ]
                full_text = lines[-1]
    
    async def ask(self, message: Message):
        '''
        Ask the message
        '''
        utils.typecheck(message, Message)
        if 'conversation' not in self.__dict__:
            self.conversation = Conversation()
        self.conversation.messages.append(message)
        ret = await self.generate_text(self.conversation)
        self.conversation.messages.append(Message(content=ret, role='agent'))
        return ret
    
class Completer(OpenAIGPT):
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
            location=CHAT_URL,
            config=config,
        )
        if not isinstance(self.config['chat'], EnhancedDict):
            raise ValueError(f'Invalid config: {self.config}')
        if not set(self.config['chat'].keys()) <= self.REQUIRE_PARAMS:
            raise ValueError(f'Unknown parameters: {set(config.keys()) - self.REQUIRE_PARAMS}')
        self.proxy:Optional[str] = self.config.get('proxy', None)
        self.api_key:str = self.config.require('openai.api_key')

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
