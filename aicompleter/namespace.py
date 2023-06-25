from typing import Any, Self, overload, TypeVar, Generator

from . import *
from .utils import *
from aicompleter.interface.command import Commands, Command
import attr

User = TypeVar('User', bound='interface.User')
Group = TypeVar('Group', bound='interface.Group')

@attr.s(auto_attribs=True, kw_only=True)
class Namespace:
    '''
    Namespace
    '''
    name: str = attr.ib(factory=str, kw_only=False)
    'The name of the namespace'
    description: str = attr.ib(factory=str)
    'The description of the namespace'
    subnamespaces: dict[str, Self] = attr.ib(factory=dict, on_setattr=attr.setters.frozen)
    'The subnamespaces of the namespace'

    commands: Commands = attr.ib(factory=Commands, on_setattr=attr.setters.frozen)
    'The commands of the namespace'
    data: EnhancedDict = attr.ib(factory=EnhancedDict, validator=attr.validators.instance_of(EnhancedDict))
    'The data of the namespace'
    config: Config = attr.ib(factory=Config, validator=attr.validators.instance_of(Config))
    'The config of the namespace'

    @subnamespaces.validator
    def __subnamespaces_validator(self, attribute: attr.Attribute, value: dict[str, Self]) -> None:
        '''
        Validate subnamespaces
        '''
        for key, val in value.items():
            if not isinstance(key, str):
                raise TypeError(f'Invalid key type: {key!r}')
            if not isinstance(val, Namespace):
                raise TypeError(f'Invalid value type: {val!r}')

    def subcmd(self, name: str) -> Command:
        '''
        Get a subcommand of the namespace
        '''
        if '.' in name:
            name, subname = name.split('.', 1)
            return self.subnamespaces[name].subcmd(subname)
        return self.commands[name]

    @overload
    def get_executable(self, user:User) -> Generator[Command, None, None]:
        ...
    
    @overload
    def get_executable(self, groupname:str) -> Generator[Command, None, None]:
        ...

    @overload
    def get_executable(self, group:Group) -> Generator[Command, None, None]:
        ...

    def get_executable(self, arg: object) -> Generator[Command, None, None]:
        '''
        Get the executable of the namespace
        *Note*: This command will yield all possible executable commands, including the name-conflicted commands in subnamespaces.
        '''
        if isinstance(arg, interface.User):
            for grp in arg.all_groups:
                yield from self.get_executable(grp)
        elif isinstance(arg, interface.Group):
            return self.get_executable(arg.name)
        elif isinstance(arg, str):
            if arg in self.subnamespaces:
                yield from self.subnamespaces[arg].get_executable(arg)
            if len(self.subnamespaces) == 0:
                # This base namespace has no subnamespaces
                for cmd in self.commands:
                    if grp in cmd.callable_groups:
                        yield cmd
        else:
            raise TypeError(f'Invalid argument type: {arg!r}')

    def reload_commands(self):
        '''
        Reload all commands
        '''
        if len(self.subnamespaces) == 0:
            # No need to reload commands
            return
        self.commands.clear()
        for sub in self.subnamespaces.values():
            sub.reload_commands()
            for cmd in sub.commands:
                if cmd.expose == False:
                    continue
                cmd.extra['from'] = sub
                self.commands.add(cmd)
