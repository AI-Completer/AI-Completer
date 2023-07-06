from __future__ import annotations

import asyncio
import enum
import json
import logging
from os import name
import time
import uuid
from typing import Any, Coroutine, Optional, TypeVar, overload

import aiohttp
import attr

import aicompleter
import aicompleter.session as session
from aicompleter import config, log
from aicompleter.config import Config, EnhancedDict

if bool(config.varibles['disable_memory']) == False:
    from aicompleter.memory.utils import MemoryConfigure
    from aicompleter.memory import (Memory, MemoryItem, VectexTransformer,
                                    getMemoryItem)

Handler = TypeVar('Handler', bound='aicompleter.handler.Handler')
User = TypeVar('User', bound='aicompleter.interface.User')
Group = TypeVar('Group', bound='aicompleter.interface.Group')
Character = TypeVar('Character', bound='aicompleter.interface.Character')
Interface = TypeVar('Interface', bound='aicompleter.interface.Interface')

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
            self.contents.append(Text(json.dumps(param, ensure_ascii=False)))
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

    @property
    def json(self) -> dict:
        '''Get json content.'''
        return json.loads(self.pure_text)

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
    def __init__(self, handler:Handler, memory:Optional['MemoryConfigure'] = None) -> None:
        self.create_time: float = time.time()
        '''Create time'''
        # self.last_used: float = self.create_time
        # '''Last used time'''
        self.history:list[Message] = []
        '''History'''
        self._closed: bool = False
        '''Closed'''
        self._id:uuid.UUID = uuid.uuid4()
        '''ID'''
        self.in_handler:Handler = handler
        '''In which handler'''
        # self.src_interface:Interface|None = None
        # '''Source interface'''
        self.config:Config = Config()
        '''Session Config'''
        self.data:EnhancedDict = EnhancedDict()
        '''Data'''
        self._running_tasks:list[asyncio.Task] = []
        '''Running tasks'''
        
        if bool(config.varibles['disable_memory']) == False:
            memory = memory or MemoryConfigure()
            self._memory:Memory = memory.initial_memory or memory.factory(*memory.factory_args, **memory.factory_kwargs)
            '''Memory'''
            self._vertex_model:VectexTransformer = VectexTransformer(memory.vertex_model)
            '''Vertex model'''
        else:
            if memory is not None:
                raise RuntimeError("Memory is disabled")
        self.logger:log.Logger=log.Logger('session')
        '''Logger'''
        formatter = log.Formatter()
        _handler = log.ConsoleHandler()
        _handler.setFormatter(formatter)
        self.logger.addHandler(_handler)
        if handler.config['global.debug']:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.push(self.id.hex[:8])

    @property
    def id(self) -> uuid.UUID:
        '''ID'''
        return self._id
    
    @property
    def extra(self) -> EnhancedDict:
        '''
        Extra information.
        Warning: This will be deprecated in the future.
        '''
        return self.data
    
    def __getitem__(self):
        return self.data.__getitem__()
    
    def __setitem__(self):
        return self.data.__setitem__()
    
    def __delitem__(self):
        return self.data.__delitem__()
    
    def __contains__(self):
        return self.data.__contains__()
    
    def __iter__(self):
        return self.data.__iter__()
    
    def __len__(self):
        return self.data.__len__()

    @property
    def closed(self) -> bool:
        return self._closed
    
    def asend(self, message:Message):
        '''Send a message.(async)'''
        if self._closed:
            raise RuntimeError("Session closed")
        return self.in_handler.asend(self,message)
    
    def send(self, message:Message):
        '''Send a message.'''
        if self._closed:
            raise RuntimeError("Session closed")
        return self.in_handler.send(self,message)

    async def close(self):
        '''Close the session.'''
        if self.closed:
            return
        self.logger.debug(f"Session closing")
        for task in self._running_tasks:
            task.cancel()
        result = await asyncio.gather(*self._running_tasks, return_exceptions=True)
        if any([isinstance(r, Exception) for r in result]):
            self.logger.exception(f"Error when closing session" + "\n".join([str(r) for r in result if isinstance(r, Exception)]))
        for interface in self.in_handler._interfaces:
            await interface.session_final(self)
        self._closed = True

    async def _update_tasks(self):
        for task in self._running_tasks:
            if task.done() or task.cancelled():
                self._running_tasks.remove(task)

@attr.s(auto_attribs=True, kw_only=True)
class Message:
    '''A normal message from the Interface.'''
    content:MultiContent = attr.ib(factory=MultiContent, converter=MultiContent)
    '''Content of the message'''
    session:Optional[Session] = attr.ib(default=None,validator=attr.validators.optional(attr.validators.instance_of(Session)))
    '''Session of the message'''
    id:uuid.UUID = attr.ib(factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID))
    '''ID of the message'''
    data:EnhancedDict = attr.ib(factory=EnhancedDict, converter=EnhancedDict, alias='extra')
    '''
    Data / Extra information
    *Note*: Deprecated.
    '''
    last_message: Optional[Message] = None
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
        return f"Called by [{self.src_interface.user.name}]: {self.content.text}"
    
    def __repr__(self) -> str:
        return f"Message({self.cmd}, {self.content.text}, {self.session.id}, {self.id})"
    
    def __to_json__(self):
        return {
            'content': self.content.pure_text,
            'session': self.session.id.hex,
            'id': self.id.hex,
            'data': self.data,
            'last_message': self.last_message.id.hex if self.last_message is not None else None,
            'cmd': self.cmd,
            'src_interface': self.src_interface.namespace if self.src_interface is not None else None,
            'dest_interface': self.dest_interface.namespace if self.dest_interface is not None else None,
        }
    
    @staticmethod
    def __from_json__(self, data:dict):
        # TODO: add session
        return Message(
            content = MultiContent(data['content']),
            session = None,
            id = uuid.UUID(data['id']),
            data = EnhancedDict(data['data']),
            last_message = uuid.UUID(data['last_message']) if data['last_message'] is not None else None,
            cmd = data['cmd'],
            src_interface = None,
            dest_interface = None,
        )
    
class MessageQueue(asyncio.Queue[Message]):
    '''Message Queue'''
    def __init__(self, id:uuid.UUID = uuid.uuid4()):
        self.id:uuid.UUID = id
        '''ID of the queue'''

