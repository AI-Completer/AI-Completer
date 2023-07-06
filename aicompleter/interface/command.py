'''
Command Support For Interface
'''
from __future__ import annotations

import asyncio
import copy
import enum
import functools
import json
import os
from typing import (Any, Callable, Coroutine, Generator, Iterable, Iterator,
                    Optional, Self, TypeVar, overload)

import attr

import aicompleter
import aicompleter.error as error
from aicompleter.session.base import MultiContent

from .. import config, log, session, utils

if bool(config.varibles['disable_memory']) == False:
    from aicompleter.memory.base import MemoryItem

Interface = TypeVar('Interface', bound='aicompleter.interface.Interface')
User = TypeVar('User', bound='aicompleter.interface.User')
Group = TypeVar('Group', bound='aicompleter.interface.Group')
Handler = TypeVar('Handler', bound='aicompleter.handler.Handler')

@attr.s(auto_attribs=True,frozen=True)
class CommandParamElement:
    '''Command Parameter Element'''
    name:str = ""
    '''Name of the parameter'''
    type:type|Callable[[Any], bool] = str
    '''
    Type of the parameter
    When callable, its value will be checked by calling this function
    The function should return boolean to adjust whether the type is right
    '''
    default:Any = None
    '''Default Value of the parameter'''
    description:str = ""
    '''Description of the parameter'''
    optional:bool = False
    '''Whether the parameter is optional'''
    tooltip:str = ""
    '''Tooltip of the parameter'''

    def __to_json__(self):
        return {
            "name":self.name,
            "type":self.type.__name__ if isinstance(self.type,type) else '',
            "default":self.default,
            "description":self.description,
            "optional":self.optional,
            "tooltip":self.tooltip,
        }
    
    @staticmethod
    def __from_json__(data:dict):
        return CommandParamElement(
            name=data['name'],
            type=eval(data['type']) if data['type'] else str,
            # TODO: fix the eval problem
            default=data['default'],
            description=data['description'],
            optional=data['optional'],
            tooltip=data['tooltip'],
        )

    @property
    def json_text(self):
        '''
        Get the json description of the parameter
        '''
        return f"<{self.type.__name__ if isinstance(self.type,type) else ''} {self.tooltip}{' = %s' % str(self.default) if self.default else ''}>"

class CommandParamStruct:
    '''
    Command Parameters Struct
    Used to test struct mainly
    '''
    @staticmethod
    def _check_struct(struct:dict|list|CommandParamElement) -> None:
        if not isinstance(struct, (dict, list, CommandParamElement)):
            raise TypeError("struct must be a dict, list or CommandParamElement instance")
        if isinstance(struct, dict):
            for i in struct:
                CommandParamStruct._check_struct(struct[i])
        elif isinstance(struct, list):
            if len(struct) != 1:
                raise TypeError("list must have only one element")
            CommandParamStruct._check_struct(struct[0])
        elif isinstance(struct, CommandParamElement):
            pass

    def __init__(self, struct:dict|list|CommandParamElement) -> None:
        self._struct = struct
        CommandParamStruct._check_struct(struct)

    def __iter__(self) -> Iterator[CommandParamElement | CommandParamStruct | list | dict]:
        '''Iterate the struct'''
        return self._struct.__iter__()
    
    def values(self) -> Iterable[CommandParamElement | CommandParamStruct | list | dict]:
        '''Iterate the struct'''
        return self._struct.values()
    
    def items(self) -> Iterable[tuple[str, CommandParamElement | CommandParamStruct | list | dict]]:
        '''Iterate the struct'''
        return self._struct.items()

    def check(self, data:dict) -> bool:
        '''Check the data to see whether it is in proper format.'''
        if isinstance(data, str):
            data = json.loads(data)

        def _check(struct:dict|list|CommandParamElement, ndata:dict):
            if isinstance(struct, dict):
                for key,value in struct.items():
                    if isinstance(value,CommandParamElement):
                        if value.optional and key not in ndata:
                            continue
                    if key not in ndata:
                        return False
                    if not _check(value, ndata[key]):
                        return False
                return True
            elif isinstance(struct, list):
                if not isinstance(ndata, list):
                    return False
                for item in ndata:
                    if not _check(struct[0], item):
                        return False
                return True
            elif isinstance(struct, CommandParamElement):
                if isinstance(struct.type, type):    
                    if not isinstance(ndata, struct.type):
                        return False
                    return True
                elif callable(struct.type):
                    if not struct.type(ndata):
                        return False
                    return True
                else:
                    raise TypeError("struct.type must be a type or a callable function")
        return _check(self._struct, data)
    
    def setdefault(self, data:dict):
        '''
        Set the default value if the parameter is optional and with default value
        '''
        data = copy.deepcopy(data)
        if isinstance(data, str):
            data = json.loads(data)

        def _set(struct:dict|list|CommandParamElement, ndata:dict):
            if isinstance(struct, dict):
                for key,value in struct.items():
                    if isinstance(value,CommandParamElement):
                        if value.optional and key not in ndata:
                            ndata[key] = value.default
                    _set(value, ndata[key])
            elif isinstance(struct, list):
                if not isinstance(ndata, list):
                    raise TypeError("data must be a list")
                for item in ndata:
                    _set(struct[0], item)
            elif isinstance(struct, CommandParamElement):
                ...

        _set(self._struct, data)
        return data
    
    def __to_json__(self):
        '''
        Get the json description of the struct
        '''
        def _json(struct:dict|list|CommandParamElement):
            if isinstance(struct, dict):
                ret = {}
                for key,value in struct.items():
                    ret[key] = _json(value)
                return ret
            elif isinstance(struct, list):
                return [_json(struct[0])]
            elif isinstance(struct, CommandParamElement):
                return json.dumps(struct.__to_json__())
            else:
                raise TypeError("struct must be a dict, list or CommandParamElement instance")
        return json.dumps(_json(self._struct))
    
    @staticmethod
    def __from_json__(data:dict):
        '''
        Get the struct from json description
        '''
        def _from_json(struct:dict|list|str):
            if isinstance(struct, dict):
                ret = {}
                for key,value in struct.items():
                    ret[key] = _from_json(value)
                return ret
            elif isinstance(struct, list):
                return [_from_json(struct[0])]
            elif isinstance(struct, str):
                return CommandParamElement.__from_json__(json.loads(struct))
            else:
                raise TypeError("struct must be a dict, list or CommandParamElement instance")
        return CommandParamStruct(_from_json(data))
    
    @property
    def json_text(self):
        '''
        Get the json description of the struct
        For example:
            {"text":<what the user input>}
        '''
        def _json_description(struct:dict|list|CommandParamElement):
            if isinstance(struct, dict):
                ret = {}
                for key,value in struct.items():
                    ret[key] = _json_description(value)
                return ret
            elif isinstance(struct, list):
                return [_json_description(struct[0])]
            elif isinstance(struct, CommandParamElement):
                return struct.json_text
            else:
                raise TypeError("struct must be a dict, list or CommandParamElement instance")
        return json.dumps(_json_description(self._struct))
    
@attr.s(auto_attribs=True)
class CommandAuthority:
    '''
    The authority of a command
    '''
    can_readfile:bool = attr.ib(default=False)
    '''Whether the command can read file'''
    can_writefile:bool = attr.ib(default=False)
    '''Whether the command can write file'''
    can_listfile:bool = attr.ib(default=False)
    '''Whether the command can list file'''
    can_execute:bool = attr.ib(default=False)
    '''Whether the command can execute the operation system command'''
    
    def get_authority_level(self):
        '''Get the authority level'''
        _level_map = {
            'can_readfile': 10,
            'can_writefile': 20,
            'can_listfile': 8,
            'can_execute': 30,
        }
        # square mean
        return sum([_level_map[i]**2 for i in self.__dict__ if self.__dict__[i] == True])**0.5


@attr.s(auto_attribs=True,hash=False)
class Command:
    '''Command Struct'''
    cmd:str = ""
    '''Command'''
    alias:set[str] = set()
    '''Alias Names'''
    description:str = ""
    '''Description For Command'''
    format:Optional[CommandParamStruct] = None
    '''Format For Command, if None, no format required'''
    callable_groups:set[str] = set()
    '''Groups who can call this command'''
    overrideable:bool = False
    '''Whether this command can be overrided by other command'''
    extra:dict = {}
    '''Extra information'''
    expose:bool = True
    '''Whether this command can be exposed to handlers'''
    authority:CommandAuthority = CommandAuthority()
    '''Authority of the command'''

    in_interface:Optional[Interface] = None
    '''Interface where the command is from'''
    callback:Optional[Callable[[session.Session, session.Message], Coroutine[Any, Any, Any]]] = None
    '''
    Call Function To Call The Command
    If None, the command will be called by in_interface
    '''
    to_return:bool = False
    '''
    Whether the command will return a value
    '''
    force_await:bool = False
    '''
    Whether the command will force await
    '''

    def __attrs_post_init__(self):
        self.logger:log.Logger = log.Logger("Command", log.INFO)
        formatter = log.Formatter([self.cmd])
        _handler = log.ConsoleHandler()
        _handler.setFormatter(formatter)
        self.logger.addHandler(_handler)
        self.logger.push(self.in_interface.user.name if self.in_interface else 'Unknown')
        self.logger.push(self.cmd)
        if bool(os.environ.get("DEBUG",False)):
            self.logger.setLevel(log.DEBUG)
        else:
            self.logger.setLevel(log.INFO)
    
    def check_support(self, handler:Handler, user:User) -> bool:
        '''Check whether the user is in callable_groups'''
        for group in handler._groupset:
            if group.name in self.callable_groups:
                if user in group:
                    return True
        return False

    async def call(self, session:session.Session, message:session.Message):
        '''Call the command'''
        if session.closed:
            raise error.SessionClosed(session,content=f"session {session.id} closed: Command.call",message=message,interface=self.in_interface)
        message.session = session
        if message.src_interface:
            # Enable self call
            if message.src_interface != message.dest_interface:
                if not self.check_support(session.in_handler, message.src_interface.user):  
                    raise error.PermissionDenied(f"user {message.src_interface.user} not in callable_groups: Command.call{str(self.callable_groups)}",message=message,interface=self.in_interface)
        self.logger.info(f"Call ({session.id}, {message.id}) {message.content}")
        message.dest_interface = self.in_interface
        if self.format != None:
            if not self.format.check(message.content.pure_text):
                raise error.FormatError(f"[Command <{self.cmd}>]format error: Command.call",message=message,interface=self.in_interface)
            message.content = MultiContent(self.format.setdefault(message.content.pure_text))
        
        # Trigger the call event
        if session.in_handler._on_call(session, message):
            # The call is interrupted
            raise error.Interrupted(f"call interrupted: Command.call",message=message,interface=self.in_interface)

        if bool(config.varibles['disable_memory']) == False:
            # Add Memory
            session._memory.put(MemoryItem(
                vertex=session._vertex_model.transform_text(message.content.pure_text),
                class_=f"cmd-{self.cmd}",
                data=message.content.pure_text,
            ))
        
        if self.callback is not None:
            task = asyncio.get_event_loop().create_task(self.callback(session, message))
            session._running_tasks.append(task)
            try:
                ret = await task
            except asyncio.CancelledError as e:
                session._running_tasks.remove(task)
                raise e
            except Exception as e:
                session._running_tasks.remove(task)
                raise e
            session._running_tasks.remove(task)
        else:   
            if self.in_interface is None:
                raise error.ParamRequired(f"[Command <{self.cmd}>]in_interface required: Command.call")
            task = asyncio.get_event_loop().create_task(self.in_interface.call(session, message))
            session._running_tasks.append(task)
            try:
                ret = await task
            except Exception as e:
                session._running_tasks.remove(task)
                raise e
            session._running_tasks.remove(task)
        if ret is not None:
            self.logger.debug("Command return value: %s" % str(ret))
        return ret
        
    def bind(self, callback:Callable[[session.Session, session.Message], None]) -> None:
        '''
        Bind a call function to the command
        If not bind, the command will be called by in_interface
        '''
        if not callable(callback):
            raise TypeError("call_func must be a callable function")
        self._call_func = callback

    def __call__(self, session:session.Session, message:session.Message) -> Coroutine[Any, Any, Any | None]:
        '''Call the command'''
        return self.call(session, message)

    def __hash__(self):
        '''Hash the command'''
        # To fix the hash error
        return hash((
            self.cmd, (*self.alias,), self.description, self.format, 
             (*self.callable_groups, ), 
            self.overrideable, tuple(self.extra.items()), 
            self.expose))
    
    def __to_json__(self):
        return {
            "cmd":self.cmd,
            "alias":list(self.alias),
            "description":self.description,
            "format":self.format.__to_json__() if self.format else None,
            "callable_groups":list(self.callable_groups),
            "overrideable":self.overrideable,
            "extra":self.extra,
            "expose":self.expose,
        }
    
    @staticmethod
    def __from_json__(data:dict):
        return Command(
            cmd=data['cmd'],
            alias=set(data.get('alias',[])),
            description=data.get('description',''),
            format=CommandParamStruct.__from_json__(data['format']) if data['format'] else None,
            callable_groups=set(data.get('callable_groups',[])),
            overrideable=bool(data.get('overrideable',False)),
            extra=data.get('extra',{}),
            expose=data.get('expose',True),
        )

class Commands(dict[str,Command]):
    '''
    Commands Dict
    '''
    @overload
    def add(self, cmd:Command) -> None:
        ...

    @overload
    def add(self, *cmds:Command) -> None:
        ...

    def add(self, *cmds:Command) -> None:
        '''Add a command to the set(not overrideable)'''
        for cmd in cmds:
            utils.typecheck(cmd, Command)
        for cmd in cmds:
            if not cmd.cmd in self:
                self.__setitem__(cmd.cmd, cmd)
                continue
            # Existed
            old_cmd = self.__getitem__(cmd.cmd)
            if old_cmd.overrideable:
                # Existed and overrideable
                self.__setitem__(cmd.cmd, cmd)
                continue
            # Existed and not overrideable
            if cmd.overrideable:
                # Existed and not overrideable and overrideable
                continue
            # Existed and not overrideable and not overrideable
            raise error.Existed(cmd.cmd, cmd_set=self)

    def __setitem__(self, __key: str, __value: Command) -> None:
        utils.typecheck(__key, str)
        utils.typecheck(__value, Command)
        if __key != __value.cmd:
            raise ValueError(f"Key {__key} must be the same as __value.cmd {__value.cmd}")
        return super().__setitem__(__key, __value)
    
    @overload
    def __contains__(self, __key: str) -> bool:
        ...

    @overload
    def __contains__(self, __key: Command) -> bool:
        ...

    @functools.singledispatchmethod
    def __contains__(self, *args, **kwargs) -> bool:
        raise TypeError("cmd must be a string instance or a Command instance")
    
    @__contains__.register(str)
    def _(self, __key: str) -> bool:
        return super().__contains__(__key)
    
    @__contains__.register(Command)
    def _(self, __key: Command) -> bool:
        return super().__contains__(__key.cmd)
    
    @overload
    def remove(self, cmd:str) -> None:
        ...

    @overload
    def remove(self, cmd:Command) -> None:
        ...

    def remove(self, cmd:object) -> None:
        '''Remove a command from the set'''
        if isinstance(cmd, str):
            if cmd in self:
                return super().__delitem__(cmd)
            raise error.NotFound(cmd, cmd_set=self)
        elif isinstance(cmd, Command):
            for i in self.values():
                if i == cmd:
                    super().__delitem__(i.cmd)
            raise error.NotFound(cmd.cmd, cmd_set=self)
        raise TypeError("cmd must be a string instance or a Command instance")

    def each(self, func:Callable[[Command], None]) -> None:
        '''Call a function for each command'''
        for i in self.values():
            func(i)

    def register(self, value:Command):
        '''
        Decorator for registering a command
        '''
        @functools.wraps(value)
        def wrapper(func:Callable[[session.Session, session.Message], None]):
            value.bind(func)
            self.add(value)
            return func
        return wrapper

    @overload
    def get_executable(self, user:User):
        ...

    @overload
    def get_executable(self, groupnmae:str):
        ...

    @overload
    def get_executable(self, group:Group):
        ...

    def get_executable(self, arg:object) -> Generator[Command, None, None]:
        '''
        Get commands executable by a user or a group
        '''
        if isinstance(arg, aicompleter.User):
            for grp in arg.all_groups:
                yield from self.get_executable(grp)
        elif isinstance(arg, aicompleter.Group):
            return self.get_executable(arg.name)
        elif isinstance(arg, str):
            for i in self.values():
                if arg in i.callable_groups:
                    yield i
        else:
            raise TypeError("arg must be a User or a Group or a string instance")

    def __repr__(self) -> str:
        return f"Commands({super().__repr__()})"

    def __iter__(self) -> Iterator[Command]:
        return self.values().__iter__()

@attr.s(auto_attribs=True)
class Result:
    '''Command Result Struct'''
    cmd:str = ""
    '''Command'''
    success:bool = True
    '''Whether the command is success'''
    ret:Any = None
    '''
    Return Value
    If not success, it will be the error
    '''
    param:Any = None
    '''
    Parameters
    If recorded
    '''
