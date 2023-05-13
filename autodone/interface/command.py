'''
Command Support For Interface
'''
from typing import (Any, Callable, Coroutine, Iterable, Iterator, Optional, TypeVar,
                    overload)

import attr

import autodone
from autodone import log
import autodone.error as error
from autodone import session
from autodone.session.base import Role

Interface = TypeVar('Interface', bound='autodone.interface.Interface')

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

    def check(self, data:dict) -> bool:
        '''Check the data to see whether it is in proper format.'''
        def _check(struct:dict|list|CommandParamElement, ndata:dict):
            if isinstance(struct, dict):
                for key,value in struct.items():
                    if isinstance(value,CommandParamElement):
                        if value.optional:
                            pass
                    if key not in ndata:
                        raise TypeError(f"key {key} not in data")
                    if not _check(value, ndata[key]):
                        return False
                return True
            elif isinstance(struct, list):
                if not isinstance(ndata, list):
                    raise TypeError("data must be a list")
                for item in ndata:
                    if not _check(struct[0], item):
                        return False
                return True
            elif isinstance(struct, CommandParamElement):
                if isinstance(struct.type, type):    
                    if not isinstance(ndata, struct.type):
                        raise TypeError(f"data must be {struct.type}")
                    return True
                elif callable(struct.type):
                    if not struct.type(ndata):
                        raise TypeError(f"data must be {struct.type}")
                    return True
        return _check(self._struct, data)

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
    callable_roles:set[Role] = set()
    '''Roles who can call this command'''
    overrideable:bool = False
    '''Whether this command can be overrided by other command'''
    extra:dict = {}
    '''Extra information'''
    expose:bool = True
    '''Whether this command can be exposed to handlers'''

    in_interface:Interface|None = None
    '''Interface where the command is from'''
    callback:Optional[Callable[[session.Session, session.Message], Coroutine[None, None, None]]] = None
    '''
    Call Function To Call The Command
    If None, the command will be called by in_interface
    '''
    def __attrs_post_init__(self):
        self.logger:log.Logger = log.Logger("Command", log.INFO)
        formatter = log.Formatter([self.cmd])
        _handler = log.ConsoleHandler()
        _handler.setFormatter(formatter)
        self.logger.addHandler(_handler)
        self.logger.push(self.cmd)
        if self.in_interface is not None:
            if self.in_interface.config['debug']:
                self.logger.setLevel(log.DEBUG)
            else:
                self.logger.setLevel(log.INFO)
    
    async def call(self, session:session.Session, message:session.Message) -> None:
        '''Call the command'''
        self.logger.info(f"Call ({session.id}, {message.id}) {message.content}")
        message.dest_interface = self.in_interface
        if self.format != None:
            if not self.format.check(message.content.pure_text):
                raise error.FormatError(f"[Command <{self.cmd}>]format error: Command.call",message=message,interface=self.in_interface)
        if self.callback is not None:
            return await self.callback(session, message)
        else:   
            if self.in_interface is None:
                raise error.ParamRequired(f"[Command <{self.cmd}>]in_interface required: Command.call")
            return await self.in_interface.call(session, message)
        
    def bind(self, callback:Callable[[session.Session, session.Message], None]) -> None:
        '''
        Bind a call function to the command
        If not bind, the command will be called by in_interface
        '''
        if not callable(callback):
            raise TypeError("call_func must be a callable function")
        self._call_func = callback

    def __call__(self, session:session.Session, message:session.Message) -> None:
        '''Call the command'''
        self.call(session, message)

    def __hash__(self):
        '''Hash the command'''
        # To fix the hash error
        return hash((
            self.cmd, (*self.alias,), self.description, self.format, 
             (*self.callable_roles, ), 
            self.overrideable, tuple(self.extra.items()), 
            self.expose))

class CommandSet:
    def __init__(self) -> None:
        self._set:set[Command] = set()

    @overload
    def add(self, cmd:Command) -> None:
        ...

    @overload
    def add(self, *cmds:Command) -> None:
        ...

    def add(self, *cmds:object) -> None:
        '''Add a command to the set(not overrideable)'''
        for cmd in cmds:
            if not isinstance(cmd, Command):
                raise TypeError("cmd must be a Command instance or an iterable object")
            if cmd in self._set:
                raise error.Existed(cmd, cmd_set=self)
            if cmd.cmd in self:
                to_raise:bool = True
                if not cmd.overrideable:
                    for i in self._set:
                        if i.overrideable:
                            if i.cmd == cmd.cmd:
                                self._set.remove(i)
                                to_raise = False
                                break
                            if cmd.cmd in i.alias:
                                i.alias.remove(cmd.cmd)
                                to_raise = False
                                break
                else:
                    to_raise = False
                    # Preserve the first command ? To be discussed
                if to_raise:
                    raise error.AliasConflict(cmd.cmd, cmd_set=self)
            self._set.add(cmd)

    def set(self, cmd:Command) -> None:
        '''Add a command to the set(overrideable)'''
        if not isinstance(cmd, Command):
            raise TypeError("cmd must be a Command instance")
        for i in self._set:
            if i.cmd == cmd.cmd:
                self._set.remove(i)
                break
            if cmd.cmd in i.alias:
                self._set.remove(i)
                break
        self._set.add(cmd)

    def remove(self, cmd:str) -> None:
        '''Remove a command from the set'''
        if not isinstance(cmd, str):
            raise TypeError("cmd must be a string instance")
        for i in self._set:
            if i.cmd == cmd:
                self._set.remove(i)
                return
            for j in i.alias:
                if j == cmd:
                    self._set.remove(i)
                    return
        raise error.NotFound(cmd, cmd_set=self)

    def get(self, cmd:str) -> Command:
        '''Get a command from the set'''
        for i in self._set:
            if i.cmd == cmd:
                return i
            for j in i.alias:
                if j == cmd:
                    return i
                
    def has(self, cmd:str) -> bool:
        '''Check if a command is in the set'''
        return cmd in [i.cmd for i in self._set] or cmd in [j for i in self._set for j in i.alias]
                
    def get_by_role(self, role:Role) -> set:
        '''Get commands callable by a role'''
        return {i for i in self._set if role in i.callable_roles}
    
    def clear(self) -> None:
        '''Clear the set'''
        self._set.clear()
                
    def __contains__(self, cmd:str) -> bool:
        return cmd in [i.cmd for i in self._set] or cmd in [j for i in self._set for j in i.alias]
    
    def __iter__(self) -> Iterator[Command]:
        return iter(self._set)
    
    def __len__(self) -> int:
        return len(self._set)
    
    def __repr__(self) -> str:
        return f"CommandSet({self._set})"
    
    def __str__(self) -> str:
        return f"CommandSet({self._set})"
    
    def __getitem__(self, cmd:str) -> Command:
        return self.get(cmd)
    
    def __setitem__(self, cmd:str, value:Command) -> None:
        self.remove(cmd)
        self.add(value)
    
