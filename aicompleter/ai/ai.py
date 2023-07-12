from __future__ import annotations

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

    config: Config = attr.ib(factory=Config, validator=attr.validators.instance_of(Config))
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
    def generate_many(self, *args, num: int,  **kwargs) -> Coroutine[list[Any], Any, None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(
            f"generate_many() is not implemented in {self.__class__.__name__}")

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
class FuncParam:
    '''
    Parameter of function
    '''
    name:str = attr.ib(converter=str)
    'Name of parameter'
    description:Optional[str] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'Description of parameter'
    type:Optional[str] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'Type of parameter'
    default:Optional[str] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'Default value of parameter'
    enum: Optional[list[str]] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.deep_iterable(member_validator=attr.validators.instance_of(str), iterable_validator=attr.validators.instance_of(list))))
    'Enum of parameter'
    required: bool = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    'Is parameter required'

    @name.validator
    def __name_validator(self, attribute, value):
        # Check illegal characters
        if not value.isidentifier():
            raise ValueError(
                f"name must be a valid identifier, not {value}")

@attr.s(auto_attribs=True)
class Function:
    '''
    Function that called by AI,
    
    # TODO
    This is a feature not fully accepted by all AI, and is related to prompts.
    We will refactor the general prompt to fit this feature.
    '''
    name:str = attr.ib(converter=str)
    'Name of function'
    description:Optional[str] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'Description of function'
    parameters: list[FuncParam] = attr.ib(factory=list, validator=attr.validators.deep_iterable(member_validator=attr.validators.instance_of(FuncParam), iterable_validator=attr.validators.instance_of(list)))

    @name.validator
    def __name_validator(self, attribute, value):
        # Check illegal characters
        if not value.isidentifier():
            raise ValueError(
                f"name must be a valid identifier, not {value}")

@attr.s(auto_attribs=True)
class Funccall:
    '''
    Function call of AI
    '''
    name: str = attr.ib(converter=str)
    'Name of function'
    function: Optional[Function] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(Function)))
    'Function of function call'
    parameters: dict[str, Any] = attr.ib(factory=dict, validator=attr.validators.deep_mapping(key_validator=attr.validators.instance_of(str), value_validator=attr.validators.instance_of(str)))
    'Parameters of function call'

@attr.s(auto_attribs=True)
class Conversation:
    '''
    Conversation
    '''
    messages: list[Message] = attr.ib(factory=list, validator=attr.validators.deep_iterable(member_validator=attr.validators.instance_of(Message), iterable_validator=attr.validators.instance_of(list)))
    'Messages of conversation'
    id: uuid.UUID = attr.ib(
        factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID))
    'ID of conversation'
    user: Optional[str] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'User of conversation'
    time: float = attr.ib(factory=time.time, validator=attr.validators.instance_of(float))
    'Creation time of conversation'
    timeout: Optional[float] = None
    'Timeout of conversation'
    data: dict = attr.ib(factory=dict, validator=attr.validators.deep_iterable(member_validator=attr.validators.instance_of(str), iterable_validator=attr.validators.instance_of(dict)))
    'Extra data of conversation'
    functions: Optional[list[Function]] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.deep_iterable(member_validator=attr.validators.instance_of(Function), iterable_validator=attr.validators.instance_of(list))))
    'Functions of conversation, this function is callable by AI, when it\'s none, no parameter will be passed to AI, note: AI may not support this feature'

    @abstractmethod
    def generate_json(self) -> dict[str, Any]:
        '''
        Generate json
        '''
        return attr.asdict(self)

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
    def generate(self, conversation: Conversation, *args, **kwargs) -> Coroutine[Message, Any, None]:
        '''
        Generate content
        '''
        return super().generate( conversation=conversation, *args, **kwargs)

    @abstractmethod
    def generate_many(self, conversation: Conversation, num: int, *args,  **kwargs) -> Coroutine[list[Message], Any, None]:
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
            yield value.content
        history.messages.append(message)
        history.messages.append(value)

    async def ask_once(self, history: Conversation, message: Message, *args, **kwargs) -> str:
        '''
        Ask the AI once
        '''
        rvalue = ''
        async for value in self.ask(history=history, message=message, *args, **kwargs):
            rvalue = value
        return rvalue
    
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
    
    async def generate_message(self, *args, **kwargs) -> Message:
        '''
        Generate message
        '''
        rvalue = None
        async for value in self.generate(*args, **kwargs):
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
