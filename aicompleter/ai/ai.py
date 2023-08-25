from __future__ import annotations

import copy
import enum
import time
import uuid
from abc import abstractmethod
from typing import Any, AsyncGenerator, Coroutine, Generator, Optional, Self, Union, final, overload

import attr

from ..utils.etype import link_property
from ..common import JSONSerializable
from ..config import Config
from ..memory import JsonMemory, Memory, MemoryItem
from . import token

@enum.unique
class AuthorType(enum.Enum):
    '''
    Type of author
    '''
    BASE = None
    '''
    The base, not anyone
    '''
    SYSTEM = 'system'
    '''
    System
    '''
    USER = 'user'
    '''
    User
    '''
    ASSISTANT = 'assistant'
    '''
    Assistant
    '''

@attr.dataclass
class AI(JSONSerializable):
    '''
    Abstract class for AI
    '''
    name: str = attr.ib(default="AI", validator=attr.validators.instance_of(str))
    'AI name'
    model: str = attr.ib(default="", validator=attr.validators.instance_of(str))
    'Model of AI'
    islocal: bool = attr.ib(default=True, validator=attr.validators.instance_of(bool))
    'Is AI local or remote'
    isenabled: bool = attr.ib(default=True, validator=attr.validators.instance_of(bool))
    'Is AI enabled'
    support: set[str] = attr.ib(default={'text'}, validator=attr.validators.deep_iterable(member_validator=attr.validators.instance_of(str), iterable_validator=attr.validators.instance_of(set)))
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
    def generate(self, *args, **kwargs) -> AsyncGenerator[Any, None]:
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
    support: set[str] = attr.ib(default={'text'}, validator=attr.validators.deep_iterable(member_validator=attr.validators.instance_of(str), iterable_validator=attr.validators.instance_of(set)))
    'Supported types of transformer'
    encoding: str = attr.ib(default="", validator=attr.validators.instance_of(str))
    'Encoding of transformer'
    max_tokens: Optional[int] = attr.ib(
        default=None, validator=attr.validators.optional(attr.validators.instance_of(int)))
    'Max tokens of transformer, will limit the length of generated content'
    
    def getToken(self, text: str) -> list[int]:
        '''
        Get token of text
        '''
        return self.encoder.encode(text)
    
    @property
    def encoder(self) -> token.Encoder:
        '''
        Get encoder
        '''
        if '_encoder' not in self.__dict__:
            if self.encoding:
                self._encoder = token.Encoder(encoding=self.encoding)
            elif self.model:
                self._encoder = token.Encoder(model=self.model)
            else:
                raise ValueError("No encoder specified")
        return self._encoder

class Embedder(Transformer):
    '''
    Abstract class for Embed transformer
    '''
    @abstractmethod
    def generate(self, prompt: str) -> AsyncGenerator[list[float], None]:
        '''
        Generate content
        *Require Coroutine*, this abstract method will raise NotImplementedError if not implemented
        '''
        raise NotImplementedError(
            f"generate() is not implemented in {self.__class__.__name__}")
    
    async def generate_embedding(self, prompt: str) -> list[float]:
        '''
        Generate embedding
        '''
        async for value in self.generate(prompt):
            pass
        return value

@attr.dataclass(init=False, str=False)
class ZipContent(JSONSerializable):
    '''
    Zipped content

    Which identifies the raw content, zipped content and omitted replacement of the raw content, this is used to slim the count of tokens and enhance the context of the AI

    Examples:
    --------
    >>> ZipContent(raw="Hello world", zip="Hello world", omitrepl="Hello world")
    ZipContent(raw='Hello world', zip='Hello world', omitrepl='Hello world')
    >>> ZipContent(raw="123456789012345678901234567890", zip="123{...}890", omitrepl="{...}")
    ZipContent(raw='123456789012345678901234567890', zip='123{...}890', omitrepl='{...}')
    '''
    raw:str = attr.ib(validator=attr.validators.instance_of(str))
    '''The raw content which will be handled by the operation system'''
    zip:str = attr.ib(validator=attr.validators.instance_of(str))
    '''The zipped content which will be sent to the AI'''
    omitrepl:Optional[str] = attr.ib(default = None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    '''The omitted replacement of the raw content'''

    @overload
    def __init__(self, content:str):
        '''
        Init from content
        '''
        pass

    @overload
    def __init__(self, right:Self):
        '''
        Init from another ZipContent
        '''
        pass
    
    @overload
    def __init__(self, raw:str, zip:str, omitrepl:Optional[str] = None):
        '''
        Init from raw, zip and omitrepl
        '''
        pass

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], self.__class__):
                self.raw = args[0].raw
                self.zip = args[0].zip
                self.omitrepl = args[0].omitrepl
            else:
                self.zip = self.raw = args[0]
                self.omitrepl = None
        elif len(args) == 3:
            self.raw = args[0]
            self.zip = args[1]
            self.omitrepl = args[2]
        else:
            raise ValueError("Invalid arguments")
        
    def __str__(self):
        return self.zip

@attr.dataclass
class Message(JSONSerializable):
    '''
    Message of conversation
    '''
    content: str = attr.ib(validator=attr.validators.instance_of(str))
    'Content of message, may be zipped in the future'
    # TODO: Add zipped content
    role: Union[str, AuthorType] = attr.ib(default=AuthorType.BASE)
    'Role of message'
    id: Optional[uuid.UUID] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(uuid.UUID)))
    'ID of message'
    user: Optional[str] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'User of message'
    time: float = attr.ib(factory=time.time, validator=attr.validators.instance_of(float))
    'Time of message'
    data: Optional[dict] = attr.ib(factory=dict, validator=attr.validators.optional(attr.validators.instance_of(dict)))
    'Extra data of message'

    author = link_property("role")

    def __str__(self):
        return self.content
    
    def __getitem__(self, index):
        return self.content[index]

    def __repr__(self):
        return f"{{content: {self.content}, role: {self.role}, id: {self.id}, user: {self.user}}}"
    
    def getMemoryItem(self) -> MemoryItem:
        '''
        Convert to memory item
        '''
        return MemoryItem(id=self.id or uuid.uuid4(), data={
            'content': self.content,
            'role': self.role,
            'user': self.user,
            'data': self.data,
        }, timestamp=self.time, user=self.user, content=self.content, category='message')

@attr.dataclass
class FuncParam(JSONSerializable):
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

@attr.dataclass
class Function(JSONSerializable):
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

@attr.dataclass
class Funccall(JSONSerializable):
    '''
    Function call of AI
    '''
    name: str = attr.ib(converter=str)
    'Name of function'
    function: Optional[Function] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(Function)))
    'Function of function call'
    parameters: dict[str, Any] = attr.ib(factory=dict, validator=attr.validators.deep_mapping(key_validator=attr.validators.instance_of(str), value_validator=attr.validators.instance_of(str)))
    'Parameters of function call'

@attr.dataclass
class Conversation(JSONSerializable):
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
    data: dict = attr.ib(factory=dict, validator=attr.validators.instance_of(dict))
    'Extra data of conversation'
    @property
    def functions(self):
        '''
        Functions of conversation, this function is callable by AI, when it\'s none, no parameter will be passed to AI, note: AI may not support this feature
        
        *Note*: Depreciated
        '''
        return self.data.get('functions', None)
    @functions.setter
    def functions(self, value):
        self.data['functions'] = value
        
    def getMemory(self, memoryFactory:type[Memory] = JsonMemory) -> Memory:
        ret = memoryFactory()
        for message in self.messages:
            ret.put(message.getMemoryItem())
        return ret
    
    def __len__(self):
        return len(self.messages)
    
    def __bool__(self):
        return True

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
    
    def update_config(self, config: Config):
        '''
        Update config, and update the dict to the varible

        Default is load config to local vars
        '''
        self.config = config

    def generate(self, conversation: Conversation, *args, **kwargs) -> AsyncGenerator[Message, None]:
        '''
        Generate content
        '''
        return super().generate( conversation=conversation, *args, **kwargs)

    def generate_many(self, conversation: Conversation, num: int, *args,  **kwargs) -> AsyncGenerator[list[Message], None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(
            f"generate_many() is not implemented in {self.__class__.__name__}")

    async def ask(self, history: Conversation, message: Message, *args, **kwargs) -> AsyncGenerator[str, None]:
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
        async for value in self.ask(history=history, message=message, *args, **kwargs):
            pass
        return value
    
    async def generate_text(self, *args, **kwargs) -> str:
        '''
        Generate text
        '''
        async for value in self.generate(*args, **kwargs):
            pass
        return value.content

    async def generate_many_texts(self, *args, num: int, **kwargs) -> list[str]:
        '''
        Generate many texts
        '''
        async for value in self.generate_many(*args, num=num, **kwargs):
            pass
        return [message.content for message in value]
    
    async def generate_message(self, *args, **kwargs) -> Message:
        '''
        Generate message
        '''
        async for value in self.generate(*args, **kwargs):
            pass
        return value

class TextTransformer(Transformer):
    '''
    Abstract class for Text transformer
    '''
    @abstractmethod
    def generate(self, prompt: str, *args,  **kwargs) -> AsyncGenerator[Message, None]:
        return super().generate(prompt=prompt, *args, **kwargs)

    def generate_many(self, prompt: str, num: int, *args,  **kwargs) -> AsyncGenerator[list[Message], None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(
            f"generate_many() is not implemented in {self.__class__.__name__}")
    
    def set_stopwords(self, stopwords: set[str]):
        '''
        Set stopwords
        '''
        raise NotImplementedError(
            f"set_stopwords() is not implemented in {self.__class__.__name__}")

class WrappedTextTransformer(ChatTransformer):
    '''
    Wrapped TextTransformer to ChatTransformer

    This class will wrap a TextTransformer to a ChatTransformer, and will add the conversation to the prompt

    Parameters:
    ----------
    wrapped: TextTransformer
        The wrapped TextTransformer
    wordend: str
        The split end of conversation, default is '<|END|>'
    init_prompt: Optional[str]
        The initial prompt of the text, default is None
    max_textlen: Optional[int]
        The max length of the text, default is None
    '''
    def __init__(self, wrapped: TextTransformer, wordend: str = '<|END|>', init_prompt: Optional[str] = None, max_textlen: Optional[int] = None):
        self.__wrapped = wrapped
        self.__wordend = wordend
        self.__init_prompt = init_prompt
        self.__max_textlen = max_textlen
        wrapped.set_stopwords([wordend])
    
    async def generate(self, conversation: Conversation, *args, **kwargs) -> AsyncGenerator[Message, None]:
        raw = self.__init_prompt or ""
        text = ""
        for message in conversation.messages:
            if message.role == AuthorType.BASE:
                text += message.content + '\n'
                continue
            if isinstance(message.role, AuthorType):
                if message.role == AuthorType.ASSISTANT:
                    role = 'you'
                else:
                    role = message.role.value
            else:
                role = message.role
            text += f'{role}: {message.content}{self.__wordend}\n'
        text += 'you: '
        if self.__max_textlen:
            if len(text) > self.__max_textlen:
                text = text[-self.__max_textlen:]
        raw = raw + text
        async for ret in self.__wrapped.generate(raw, *args, **kwargs):
            ret.role = AuthorType.ASSISTANT
            yield ret

    async def generate_many(self, conversation: Conversation, num: int, *args, **kwargs) -> AsyncGenerator[list[Message], None]:
        raw = self.__init_prompt or ""
        text = ""
        for message in conversation.messages:
            if message.role == AuthorType.BASE:
                text += message.content + '\n'
                continue
            if isinstance(message.role, AuthorType):
                if message.role == AuthorType.ASSISTANT:
                    role = 'you'
                else:
                    role = message.role.value
            else:
                role = message.role
            text += f'{role}: {message.content}{self.__wordend}\n'
        text += 'you: '
        if self.__max_textlen:
            if len(text) > self.__max_textlen:
                text = text[-self.__max_textlen:]
        async for ret in self.__wrapped.generate_many(raw, num, *args, **kwargs):
            for retmsg in ret:
                retmsg.role = AuthorType.ASSISTANT
            yield ret

    def __getattribute__(self, __name: str) -> Any:
        if __name.startswith('_WrappedTextTransformer__'):
            return super().__getattribute__(__name)
        elif hasattr(ChatTransformer, __name) and callable(getattr(ChatTransformer, __name)):
            return super().__getattribute__(__name)
        else:
            return getattr(self.__wrapped, __name)
    
    def __setattr__(self, name: str, value: Any):
        if name.startswith('_WrappedTextTransformer__'):
            super().__setattr__(name, value)
        else:
            setattr(self.__wrapped, name, value)

    def __delattr__(self, __name: str) -> None:
        if __name.startswith('_WrappedTextTransformer__'):
            super().__delattr__(__name)
        else:
            delattr(self.__wrapped, __name)


