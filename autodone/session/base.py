from __future__ import annotations
import enum
import aiohttp
from autodone.handler import Handler
from autodone.interface.base import Character, Interface
import autodone.session as session
import attr
import json
import logging
import uuid
import time
import asyncio
from autodone.interface import Role

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
    def __init__(self) -> None:
        self.contents:list[Content] = []

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
    LOGGER=logging.getLogger(__name__)
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
        self.roles:list[Role] = []
        '''Role list'''
        self.active_role:Role|None = None
        '''Active role'''
        self.id:uuid.UUID = uuid.uuid4()
        '''ID'''
        self.in_handler:Handler = handler
        '''In which handler'''
        self.src_interface:Interface|None = None
        '''Source interface'''
        self.extra:dict = {
            'http_session':aiohttp.ClientSession(),
        }
        '''Extra information'''

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

@attr.s(auto_attribs=True, frozen=True)
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

    src_interface:Interface|None = None
    '''Interface which send this message'''
    dest_interface:Interface|None = None
    '''Interface which receive this message'''

    _status:MessageStatus = MessageStatus.NOT_SENT
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
    
class MessageQueue(asyncio.Queue[session.Message]):
    '''Message Queue'''
    def __init__(self, id:uuid.UUID = uuid.uuid4()):
        self.id:uuid.UUID = id
        '''ID of the queue'''

