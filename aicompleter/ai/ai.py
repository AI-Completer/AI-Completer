import copy
import time
import uuid
from abc import abstractmethod
from typing import Any, Coroutine, Optional

import attr

from aicompleter.config import Config


@attr.s(auto_attribs=True)
class AI:
    '''
    Abstract class for AI
    '''
    name: str = attr.ib(default="AI", converter=str)
    'AI name'
    islocal: bool = attr.ib(default=True, converter=bool)
    'Is AI local or remote'
    isenabled: bool = attr.ib(default=True, converter=bool)
    'Is AI enabled'
    support: set[str] = attr.ib(default={'text'}, converter=set)
    'Supported types of AI'
    location: Optional[str] = attr.ib(
        default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'Location of AI'

    config: Config = attr.ib(factory=Config, on_setattr=attr.setters.convert)
    'Config of AI'

    @property
    def support_text(self):
        return 'text' in self.support

    @property
    def support_image(self):
        return 'image' in self.support

    @abstractmethod
    def generate(self, *args, **kwargs):
        '''
        Generate content
        *Require Coroutine*, this abstract method will raise NotImplementedError if not implemented
        '''
        raise NotImplementedError(
            f"generate() is not implemented in {self.__class__.__name__}")


class Transformer(AI):
    '''
    Abstract class for transformer
    '''
    support = {'text'}
    'Supported types of transformer'
    encoding: str
    'Encoding of transformer'
    max_tokens: Optional[int] = None
    'Max tokens of transformer, will limit the length of generated content'

    @abstractmethod
    def generate_many(self, *args, num: int,  **kwargs) -> Coroutine[list[str], Any, None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(
            f"generate_many() is not implemented in {self.__class__.__name__}")

    async def generate_text(self, *args, **kwargs) -> str:
        '''
        Generate text
        '''
        rvalue = ''
        async for value in self.generate(*args, **kwargs):
            rvalue = value
        return rvalue

    async def generate_many_texts(self, *args, num: int, **kwargs) -> list[str]:
        '''
        Generate many texts
        '''
        rvalue = []
        async for value in self.generate_many(*args, num=num, **kwargs):
            rvalue = value
        return rvalue


@attr.s(auto_attribs=True)
class Message:
    '''
    Message of conversation
    '''
    content: str
    'Content of message'
    role: str
    'Role of message'
    id: Optional[uuid.UUID] = None
    'ID of message'
    user: Optional[str] = None
    'User of message'
    time: float = time.time()
    'Time of message'
    data: dict = {}
    'Extra data of message'

    def __str__(self):
        return self.content

    def __repr__(self):
        return f"{{content: {self.content}, role: {self.role}, id: {self.id}, user: {self.user}}}"

@attr.s(auto_attribs=True)
class Conversation:
    '''
    Conversation
    '''
    messages: list[Message] = []
    'Messages of conversation'
    id: uuid.UUID = attr.ib(
        factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID))
    'ID of conversation'
    user: Optional[str] = None
    'User of conversation'
    time: float = time.time()
    'Creation time of conversation'
    timeout: Optional[float] = None
    'Timeout of conversation'
    data: dict = {}
    'Extra data of conversation'


class ChatTransformer(Transformer):
    '''
    Abstract class for Chatable transformer
    '''

    def new_conversation(self, user: Optional[str] = None, id: Optional[uuid.UUID] = None, init_prompt: Optional[str] = None) -> Conversation:
        '''
        Create a new conversation
        '''
        ret = Conversation(user=user, id=id or uuid.uuid4())
        if init_prompt:
            ret.messages.append(
                Message(content=init_prompt, role='system', user=user))
        return ret

    @abstractmethod
    def generate(self, conversation: Conversation, *args, **kwargs) -> Coroutine[str, Any, None]:
        '''
        Generate content
        '''
        return super().generate( conversation=conversation, *args, **kwargs)

    @abstractmethod
    def generate_many(self, conversation: Conversation, num: int, *args,  **kwargs) -> Coroutine[list[str], Any, None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(
            f"generate_many() is not implemented in {self.__class__.__name__}")

    async def ask(self, history: Conversation, message: Message, *args, **kwargs) -> Coroutine[str, Any, None]:
        '''
        Ask the AI
        '''
        # If this function is not inherited, it will use generate() instead
        new_conversation = copy.deepcopy(history)
        new_conversation.messages.append(message)
        async for value in self.generate(*args, conversation=new_conversation, **kwargs):
            yield value
        history.messages.append(message)
        history.messages.append(
            Message(content=value, role='assistant', user=history.user))

    async def ask_once(self, history: Conversation, message: Message, *args, **kwargs) -> str:
        '''
        Ask the AI once
        '''
        rvalue = ''
        async for value in self.ask(history=history, message=message, *args, **kwargs):
            rvalue = value
        return rvalue

class TextTransformer(Transformer):
    '''
    Abstract class for Text transformer
    '''
    @abstractmethod
    async def generate(self, *args, prompt: str, **kwargs) -> Coroutine[str, Any, None]:
        return super().generate(*args, prompt=prompt, **kwargs)

    @abstractmethod
    async def generate_many(self, *args, prompt: str, num: int,  **kwargs) -> Coroutine[list[str], Any, None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(
            f"generate_many() is not implemented in {self.__class__.__name__}")
