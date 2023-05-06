'''
Command Support For Interface
'''
import attr
from autodone.session.base import Role, System, User, Agent
import autodone.error as error

@attr.s(auto_attribs=True,frozen=True)
class Command:
    '''Command Struct'''
    cmd:str = ""
    '''Command'''
    alias:list[str] = ""
    '''Alias Names'''
    description:str = ""
    '''Description For Command'''
    callable_role:list[Role] = []
    '''Roles who can call this command'''
    overrideable:bool = False
    '''Whether this command can be overrided by other command'''

class CommandSet:
    def __init__(self) -> None:
        self._set:set[Command] = set()

    def add(self, cmd:Command) -> None:
        '''Add a command to the set(not overrideable)'''
        if not isinstance(cmd, Command):
            raise TypeError("cmd must be a Command instance")
        if cmd in self._set:
            raise error.Existed(cmd, cmd_set=self)
        if cmd.cmd in self:
            to_raise:bool = True
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
                
    def __contains__(self, cmd:str) -> bool:
        return cmd in [i.cmd for i in self._set] or cmd in [j for i in self._set for j in i.alias]
    
    def __iter__(self) -> iter:
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
    