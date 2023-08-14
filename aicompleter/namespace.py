import asyncio
from typing import Any, Iterator, Self, overload, TypeVar, Generator

from . import *
from .utils import *
from aicompleter.interface.command import Commands, Command
import attr

User = TypeVar('User', bound='interface.User')
Group = TypeVar('Group', bound='interface.Group')

@attr.dataclass(kw_only=False)
class BaseNamespace:
    name: str = attr.ib(default="")
    'The name of the namespace'
    description: str = attr.ib(default="")
    'The description of the namespace'

@attr.dataclass(kw_only=True)
class Namespace(BaseNamespace):
    '''
    Namespace
    '''
    subnamespaces: dict[str, Self] = attr.ib(factory=dict, on_setattr=attr.setters.frozen)
    'The subnamespaces of the namespace'
    commands: Commands = attr.ib(factory=Commands, on_setattr=attr.setters.frozen)
    'The commands of the namespace'
    data: EnhancedDict = attr.ib(factory=EnhancedDict, validator=attr.validators.instance_of(EnhancedDict))
    'The data of the namespace'
    config: Config = attr.ib(factory=Config, validator=attr.validators.instance_of(Config))
    'The config of the namespace'

    def __attrs_post_init__(self):
        '''
        Post init
        '''
        self.onConfigChange = events.Event(type=events.Type.Hook)
        '''Event that will be triggered when the config is changed'''
        # Warning: This may raise the disorder of the execution order
        # TODO: Find a better way to do this
        def _on_change(key, value):
            asyncio.get_running_loop().create_task(self.onConfigChange(key, value))
        self.config.__on_setter__ = _on_change

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
    def get_executable(self, user:User) -> Iterator[Command]:
        ...
    
    @overload
    def get_executable(self, groupname:str) -> Iterator[Command]:
        ...

    @overload
    def get_executable(self, group:Group) -> Iterator[Command]:
        ...

    @overload
    def get_executable(self) -> Iterator[Command]:
        ...

    def get_executable(self, arg: object = None) -> Iterator[Command]:
        '''
        Get the executable of the namespace
        *Note*: This command will yield all possible executable commands, including the name-conflicted commands in subnamespaces.
        '''
        from . import interface
        if arg == None:
            yield from self.commands
            for namespace in self.subnamespaces.values():
                yield from namespace.commands
        elif isinstance(arg, interface.User):
            for grp in arg.all_groups:
                yield from self.get_executable(grp)
        elif isinstance(arg, interface.Group):
            return self.get_executable(arg.name)
        elif isinstance(arg, str):
            for cmd in self.commands:
                if arg in cmd.callable_groups:
                    yield cmd
            for value in self.subnamespaces.values():
                yield from value.get_executable(arg)
        else:
            raise TypeError(f'Invalid argument type: {arg!r}')

    def subnamespace(self, name:str):
        if self.name == name:
            yield self
        for value in self.subnamespaces.values():
            yield from value.subnamespace(name)

    def getcmd(self, name:str):
        if name in self.commands:
            yield self.commands[name]
        for value in self.subnamespaces.values():
            yield from value.getcmd(name)
    