from __future__ import annotations

import asyncio
import enum
import json
import logging
import time
import uuid
from typing import Any, Coroutine, Optional, TypeVar, overload

import aiohttp
import attr

import autodone
import autodone.session as session
from autodone import log
from autodone.config import EnhancedDict
from autodone.utils import defaultdict

Handler = TypeVar('Handler', bound='autodone.handler.Handler')
User = TypeVar('User', bound='autodone.interface.User')
Group = TypeVar('Group', bound='autodone.interface.Group')
Character = TypeVar('Character', bound='autodone.interface.Character')
Interface = TypeVar('Interface', bound='autodone.interface.Interface')

class Content(object):
    '''Common content class.'''

class Text(Content,str):
    '''Text content.'''

class Image(Content):
    '''Image content.'''
    def __init__(self, url:str) -> None:
        self.url = url

    def __str__(self) -> str:
        return f"![{self.url}]({self.url})"
    
    def __repr__(self) -> str:
        return f"Image({self.url})"

class Audio(Content):
    '''Audio content.'''
    def __init__(self, url:str) -> None:
        self.url = url

    def __str__(self) -> str:
        return f"![{self.url}]({self.url})"
    
    def __repr__(self) -> str:
        return f"Audio({self.url})"

class MultiContent(Content):
    '''Combine text, images and audios.'''
    @overload
    def __init__(self) -> None:
        ...

    @overload
    def __init__(self, text:str) -> None:
        ...

    @overload
    def __init__(self, contents:list[Content]) -> None:
        ...

    def __init__(self, param) -> None:
        self.contents:list[Content] = []
        if isinstance(param, str):
            self.contents.append(Text(param))
        elif isinstance(param, list):
            self.contents.extend(param)
        elif isinstance(param, dict):
            self.contents.append(Text(json.dumps(param)))
        elif param is None:
            pass
        else:
            raise TypeError(f"Unsupported type {type(param)}")

    def add(self, content:Content) -> None:
        '''Add a content.'''
        self.contents.append(content)
    
    def remove(self, content:Content) -> None:
        '''Remove a content.'''
        self.contents.remove(content)

    @property
    def text(self) -> str:
        '''Get text content.'''
        return "".join([str(content) for content in self.contents])

    @property
    def pure_text(self) -> str:
        '''Get pure text content.'''
        return "".join([str(content) for content in self.contents if isinstance(content, Text)])
    
    @property
    def images(self) -> list[Image]:
        '''Get image content.'''
        return [content for content in self.contents if isinstance(content, Image)]
    
    @property
    def audios(self) -> list[Audio]:
        '''Get audio content.'''
        return [content for content in self.contents if isinstance(content, Audio)]
    
    def __str__(self):
        return self.text

    def __json__(self):
        return self.text

@enum.unique
class MessageStatus(enum.Enum):
    '''Message status.'''
    NOT_SENT = enum.auto()
    '''Not sent.'''
    ON_SENDING = enum.auto()
    '''On sending.'''
    SENT = enum.auto()
    '''Sent.'''

class Session:
    '''Session'''
    def __init__(self, handler:Handler) -> None:
        self.create_time: float = time.time()
        '''Create time'''
        self.last_used: float = self.create_time
        '''Last used time'''
        self.history:list[Message] = []
        '''History'''
        self.lock: asyncio.Lock = asyncio.Lock()
        '''Lock'''
        self._closed: bool = False
        '''Closed'''
        self._id:uuid.UUID = uuid.uuid4()
        '''ID'''
        self.in_handler:Handler = handler
        '''In which handler'''
        self.src_interface:Interface|None = None
        '''Source interface'''
        self.extra:EnhancedDict = EnhancedDict()
        '''Extra information'''

        self.logger:log.Logger=log.Logger('session')
        '''Logger'''
        formatter = log.Formatter()
        _handler = log.ConsoleHandler()
        _handler.setFormatter(formatter)
        self.logger.addHandler(_handler)
        if handler.global_config['debug']:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.push(self.id.hex[:8])

    @property
    def id(self) -> uuid.UUID:
        '''ID'''
        return self._id

    async def acquire(self) -> None:
        '''Lock the session.'''
        await self.lock.acquire()
        self.last_used = time.time()
    
    def release(self) -> None:
        '''Release the session.'''
        self.lock.release()
    
    async def __aenter__(self) -> Session:
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.release()

    @property
    def locked(self) -> bool:
        return self.lock.locked()
    
    def __getitem__(self):
        return self.extra.__getitem__()
    
    def __setitem__(self):
        return self.extra.__setitem__()
    
    def __delitem__(self):
        return self.extra.__delitem__()
    
    def __contains__(self):
        return self.extra.__contains__()
    
    def __iter__(self):
        return self.extra.__iter__()
    
    def __len__(self):
        return self.extra.__len__()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.http_session.close()
    
    @property
    def closed(self) -> bool:
        return self._closed
    
    def asend(self, message:Message) -> Coroutine[Any, Any, None]:
        '''Send a message.(async)'''
        if self._closed:
            raise RuntimeError("Session closed")
        return self.in_handler.asend(self,message)
    
    def send(self, message:Message):
        '''Send a message.'''
        if self._closed:
            raise RuntimeError("Session closed")
        self.in_handler.send(self,message)

    async def start(self, interface:Interface, cmd:str, data:Any, awaitable:bool = True):
        '''Start a session.'''
        if self.closed:
            raise RuntimeError("Session closed")
        try:
            message = Message(
                content=MultiContent({
                    "interface-name":interface.user.name,
                    "command":cmd,
                    "data":str(data)
                }),
                session=self,
                cmd="init",
                dest_interface=[i for i in self.in_handler.interfaces if i.user.name == 'initializer'][0]
            )
        except IndexError:
            raise RuntimeError("Interface[Initializer] not found")
        await self.asend(message) if awaitable else self.send(message)

    async def close(self):
        '''Close the session.'''
        if self.closed:
            return
        self.logger.debug(f"Session closing")
        for interface in self.in_handler._interfaces:
            await interface.session_final(self)
        self._closed = True

@attr.s(auto_attribs=True, kw_only=True)
class Message:
    '''A normal message from the Interface.'''
    content:MultiContent
    '''Content of the message'''
    session:Session = session
    '''Session of the message'''
    id:uuid.UUID = uuid.uuid4()
    '''ID of the message'''
    extra:dict = {}
    '''Extra information'''
    last_message:Message|None = None
    '''Last message'''
    cmd:str
    '''Call which command to transfer this Message'''

    src_interface:Optional[Interface] = None
    '''Interface which send this message'''
    dest_interface:Optional[Interface] = None
    '''Interface which receive this message'''

    def __attrs_post_init__(self) -> None:
        self._status:MessageStatus = MessageStatus.NOT_SENT

        if not isinstance(self.content, MultiContent):
            self.content = MultiContent(self.content)
    
    '''
    Status of the message.
    '''
    @property
    def status(self) -> MessageStatus:
        return self._status
    
    @status.setter
    def status(self, value:MessageStatus) -> None:
        '''
        Set status of the message.
        Note that you can only set status to more advanced status.
        '''
        if value.value <= self._status.value:
            raise ValueError(f"Cannot set status to {value.name} from {self._status.name}")
        self._status = value
        if value == MessageStatus.SENT and self.session is not None and self._status != MessageStatus.SENT:
            self.session.history.append(self)

    def __str__(self) -> str:
        return f"{self.character.name}: {self.content.text}"
    
    def __repr__(self) -> str:
        return f"Message({self.character.name}, {self.content.text}, {self.session.id}, {self.id})"
    
class MessageQueue(asyncio.Queue[Message]):
    '''Message Queue'''
    def __init__(self, id:uuid.UUID = uuid.uuid4()):
        self.id:uuid.UUID = id
        '''ID of the queue'''

