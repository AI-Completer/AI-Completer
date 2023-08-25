from __future__ import annotations

import asyncio
import enum
import json
import time
import uuid
from asyncio import CancelledError
from typing import Any, Coroutine, Optional, Self, TypeVar, overload

import attr

import aicompleter

from .. import config, events, log, utils
from ..config import Config, EnhancedDict
from ..utils.special import getcallercommand

Handler = TypeVar('Handler', bound='aicompleter.handler.Handler')
User = TypeVar('User', bound='aicompleter.interface.User')
Group = TypeVar('Group', bound='aicompleter.interface.Group')
Character = TypeVar('Character', bound='aicompleter.interface.Character')
Interface = TypeVar('Interface', bound='aicompleter.interface.Interface')
Command = TypeVar('Command', bound='aicompleter.interface.Command')

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

    @overload
    def __init__(self, json: dict|list) -> None:
        ...

    def __init__(self, param:str|list[Content]|dict|list|Self|type(None) = None) -> None:
        self.contents:list[Content] = []
        if isinstance(param, str):
            self.contents.append(Text(param))
        elif isinstance(param, list):
            self.contents.extend(param)
        elif isinstance(param, dict):
            self.contents.append(Text(json.dumps(param, ensure_ascii=False)))
        elif param is None:
            pass
        elif isinstance(param, type(self)):
            self.contents.extend(param.contents)
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
    
    def __getitem__(self, key):
        return self.json[key]

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
        self.config:Config = Config()
        '''Session Config'''
        self.data:EnhancedDict = EnhancedDict()
        '''Data'''
        self._running_tasks: utils.TaskList = utils.TaskList()
        '''Running tasks'''
        self._running_commands: list[tuple[aicompleter.Command, Message]] = []
        '''
        Running commands.

        This is a list of tuple of command and message, containing all running commands.
        '''
        self.on_call: events.Event = events.Event(type=events.Type.Hook)
        '''
        Event of Call, this will be triggered when a command is called
        If the event is stopped, the command will not be called
        '''
        
        self.logger:log.Logger=log.Logger('session')
        '''Logger'''
        self.logger = log.getLogger('Session', [self.id.hex[:8]])

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
    
    @overload
    def asend(self, message:Message) -> Coroutine[None, None, Any]:
        ...

    @overload
    def asend(self, cmd:str, 
            content:MultiContent = MultiContent(),
            *,
            data:EnhancedDict = EnhancedDict(), 
            last_message: Optional[Message] = None,
            src_interface:Optional[Interface] = None,
            dest_interface:Optional[Interface] = None,
        ) -> Coroutine[None, None, Any]:
        ...
    
    def asend(self, cmd_or_msg:str|Message, 
            content:Optional[MultiContent] = None,
            *args, **kwargs
        ) -> Coroutine[None, None, Any]:
        '''Send a message.(async)'''
        if isinstance(cmd_or_msg, Message):
            if content is not None or len(args) or len(kwargs):
                raise ValueError("Cannot specify content or args or kwargs when sending a Message")
            if self._closed:
                raise RuntimeError("Session closed")
            
            if cmd_or_msg.src_interface is None:
                callercommand = getcallercommand(commands=self.in_handler.get_executable_cmds())
                if callercommand is not None:
                    cmd_or_msg.src_interface = callercommand.in_interface
            cmd_or_msg._check_cache['src_interface'] = True
            
            return self.in_handler.call(self, cmd_or_msg)
        elif isinstance(cmd_or_msg, str):
            params = {
                'cmd': cmd_or_msg,
                'content': content or MultiContent(),
                'data': kwargs.pop('data', EnhancedDict()),
                'last_message': kwargs.pop('last_message', None),
                'src_interface': kwargs.pop('src_interface', None),
                'dest_interface': kwargs.pop('dest_interface', None),
            }
            if len(args) or len(kwargs):
                raise ValueError("Cannot specify args or kwargs when sending a cmd")
            if self._closed:
                raise RuntimeError("Session closed")
            
            if params['src_interface'] is None:
                callercommand = getcallercommand(commands=self.in_handler.get_executable_cmds())
                if callercommand is not None:
                    params['src_interface'] = callercommand.in_interface
            msg = Message(**params)
            msg._check_cache['src_interface'] = True

            return self.in_handler.call(self, msg)
        else:
            raise TypeError(f"Unsupported type {type(cmd_or_msg)}")
    
    @overload
    def send(self, message:Message) -> None:
        ...

    @overload
    def send(self, cmd:str, 
            content:MultiContent = MultiContent(),
            *,
            data:EnhancedDict = EnhancedDict(), 
            last_message: Optional[Message] = None,
            src_interface:Optional[Interface] = None,
            dest_interface:Optional[Interface] = None,
        ) -> None:
        ...
    
    def send(self, cmd_or_msg:str|Message, 
            content:Optional[MultiContent] = None,
            *args, **kwargs
        ) -> None:
        '''Send a message.'''
        if isinstance(cmd_or_msg, Message):
            if content is not None or len(args) or len(kwargs):
                raise ValueError("Cannot specify content or args or kwargs when sending a Message")
            if self._closed:
                raise RuntimeError("Session closed")
            return self.in_handler.call_soon(self, cmd_or_msg)
        elif isinstance(cmd_or_msg, str):
            params = {
                'cmd': cmd_or_msg,
                'content': content or MultiContent(),
                'data': kwargs.pop('data', EnhancedDict()),
                'last_message': kwargs.pop('last_message', None),
                'src_interface': kwargs.pop('src_interface', None),
                'dest_interface': kwargs.pop('dest_interface', None),
            }
            if len(args) or len(kwargs):
                raise ValueError("Cannot specify args or kwargs when sending a cmd")
            if self._closed:
                raise RuntimeError("Session closed")
            return self.in_handler.call_soon(self, Message(**params))
        else:
            raise TypeError(f"Unsupported type {type(cmd_or_msg)}")
        
    async def _init_session(self):
        tasks = []
        loop = self.in_handler._loop
        for interface in self.in_handler.interfaces:
            tasks.append(loop.create_task(interface._invoke_session_init(self)))
        await asyncio.gather(*tasks)

    async def close(self):
        '''Close the session.'''
        if self.closed:
            return
        self.logger.debug(f"Session closing")
        for task in self._running_tasks:
            task.cancel()
        result = await asyncio.gather(*self._running_tasks, return_exceptions=True)
        if any([isinstance(r, Exception) and not isinstance(r, CancelledError) for r in result]):
            self.logger.exception(f"Error when closing session" + "\n".join([str(r) for r in result if isinstance(r, Exception)]))
        tasks = []
        loop = self.in_handler._loop
        for interface in self.in_handler._interfaces:
            tasks.append(loop.create_task(interface._invoke_session_final(self)))
        await asyncio.gather(*tasks)
        self._closed = True

    async def _update_tasks(self):
        for task in self._running_tasks:
            if task.done() or task.cancelled():
                self._running_tasks.remove(task)

    def get_data(self):
        ret = {
            'id': self.id.hex,
            'config': self.config,
            'storage': []
        }
        for i in self.in_handler._interfaces:
            data = i.getStorage(self)
            if data == None:
                continue
            ret['storage'].append({
                'id': i.id.hex,
                'data': data
            })
        return ret
    
    def save(self, storage: utils.StorageManager | str):
        if isinstance(storage, str):
            storage = utils.StorageManager(storage)
        meta = {
            'id': self.id.hex,
            'config': dict(self.config),
            'created_time': self.create_time,
            'closed': self._closed,
        }
        with open(storage.alloc_file('meta'), 'w') as f:
            json.dump(meta, f)
        for i in self.in_handler._interfaces:
            i.save_session(storage.alloc_file({
                'type': 'interface',
                'id': i.id.hex,
            }), self)
        for i in self.history:
            i.save(storage.alloc_file({
                'type': 'message',
                'id': i.id.hex,
            }))
        storage.save()

    @classmethod
    def load(cls, storage: utils.StorageManager | str, in_handler: Handler):
        if isinstance(storage, str):
            storage = utils.StorageManager.load(storage)
        with open(storage['meta'].path, 'r') as f:
            meta = json.load(f)
        session = cls(handler=in_handler)
        session.create_time = meta['created_time']
        session.config = Config(meta['config'])
        session._closed = meta['closed']
        session._id = uuid.UUID(meta['id'])
        intmap = {}
        hislis = []
        for i in storage:
            if not isinstance(i.mark, dict) or 'type' not in i.mark:
                continue
            if i.mark['type'] == 'interface':
                intmap[i.mark['id']] = storage[i.mark]
            elif i.mark['type'] == 'message':
                hislis.append(storage[i.mark])
        for i in in_handler._interfaces:
            # If not found, will throw KeyError
            i.load_session(storage[intmap.pop(i.id.hex).mark].path, session)
        for i in hislis:
            session.history.append(Message.load(i.path, session))
        if len(intmap):
            log.warning(f"Interfaces(ID-baesd) not found: {intmap.keys()}. Are the interfaces changed?")
        return session

# Limited by the attrs module, the performance of attr on kw_only is not overridable by the attribute.
@attr.dataclass(kw_only=False)
class BaseMessage:
    '''
    Base Message class.
    '''
    cmd:str = attr.ib(default="")
    '''Call which command to transfer this Message'''
    content:MultiContent = attr.ib(factory=MultiContent, converter=MultiContent)
    '''Content of the message'''

@attr.dataclass(kw_only=True)
class Message(BaseMessage):
    '''A normal message from the Interface.'''
    session:Optional[Session] = attr.ib(default=None,validator=attr.validators.optional(attr.validators.instance_of(Session)))
    '''Session of the message'''
    id:uuid.UUID = attr.ib(factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID))
    '''ID of the message'''
    data:EnhancedDict = attr.ib(factory=EnhancedDict, converter=EnhancedDict)
    '''Data information'''
    last_message: Optional[Message] = None
    '''Last message'''

    src_interface:Optional[Interface] = None
    '''Interface which send this message'''
    dest_interface:Optional[Interface] = None
    '''Interface which receive this message'''

    _check_cache:dict = attr.ib(factory=dict, init=False)

    def __attrs_post_init__(self) -> None:
        self._status:MessageStatus = MessageStatus.NOT_SENT
    
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
            if not self in self.session.history:
                self.session.history.append(self)

    def __str__(self) -> str:
        return self.content.pure_text
    
    def __repr__(self) -> str:
        return f"Message({self.cmd}, {self.content.text}, {self.session.id}, {self.id})"
    
    def to_json(self):
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
    
    @classmethod
    def from_json(cls, data:dict):
        # TODO: add session
        return cls(
            content = MultiContent(data['content']),
            session = None,
            id = uuid.UUID(data['id']),
            data = EnhancedDict(data['data']),
            last_message = None,
            cmd = data['cmd'],
            src_interface = None,
            dest_interface = None,
        )
    
    def __getitem__(self, key):
        return self.content[key]
    
    def __setitem__(self, key, value):
        self.content[key] = value

    def get(self, key, default=...):
        if default is ...:
            return self.content[key]
        else:
            return self.content.json.get(key, default)
        
    def save(self, file:str):
        with open(file, 'w') as f:
            json.dump(self.to_json(), f)

    @classmethod
    def load(cls, file:str, session:Session):
        with open(file, 'r') as f:
            data = json.load(f)
        msg = cls.from_json(data)
        msg.session = session
        if data['last_message'] is not None:
            for i in session.history:
                if i.id.hex == data['last_message']:
                    msg.last_message = i
                    break
            else:
                log.warning(f"Last message not found: {data['last_message']}")
        if data['src_interface'] is not None:
            for i in session.in_handler._interfaces:
                if i.id == data['src_interface']:
                    msg.src_interface = i
                    break
            else:
                log.warning(f"Source interface not found: {data['src_interface']}")
        if data['dest_interface'] is not None:
            for i in session.in_handler._interfaces:
                if i.id == data['dest_interface']:
                    msg.dest_interface = i
                    break
            else:
                log.warning(f"Destination interface not found: {data['dest_interface']}")
        return msg
    
class MessageQueue(asyncio.Queue[Message]):
    '''Message Queue'''
    def __init__(self, id:uuid.UUID = uuid.uuid4()):
        self.id:uuid.UUID = id
        '''ID of the queue'''

