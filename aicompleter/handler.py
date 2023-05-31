'''
Handler between the interfaces
'''
import asyncio
import copy
import uuid
from typing import Generator, Iterator, Optional, overload

from . import error, events, interface, log, session
from .config import Config
from .interface import Command, Interface, User, Group, UserSet, GroupSet
from .interface.command import CommandSet, Commands
from .session.base import Session

class Handler:
    '''
    Handler for AutoDone-AI
    The handler will transfer various information between Interfaces, 
    enabling interaction among person, AI and system.
    '''
    @overload
    def __init__(self) -> None:
        pass

    @overload
    def __init__(self, config:Config) -> None:
        pass

    def __init__(self, config:Optional[Config] = Config()) -> None:
        self._interfaces:set[Interface] = set()
        self._commands:Commands = Commands()
        # self._call_queues:list[tuple[session.Session, session.Message]] = []
        self._closed:asyncio.Event = asyncio.Event()
        '''Closed'''
        self.config:Config = config
        '''Config of Handler'''
        self.on_exception:events.Exception = events.Exception(Exception)
        '''Event of Exception'''
        self.on_keyboardinterrupt:events.Exception = events.Exception(KeyboardInterrupt)
        '''Event of KeyboardInterrupt'''
        self._userset:UserSet = UserSet()
        '''User Set of Handler'''
        self._groupset:GroupSet = GroupSet()
        '''Group Set of Handler'''

        async def _default_exception_handler(e:Exception, obj:object):
            self.logger.exception(e)

        self.on_exception.add_callback(_default_exception_handler)
        
        self.on_keyboardinterrupt.add_callback(lambda e,obj:self.close())

        self.logger:log.Logger = log.Logger("Handler")
        '''Logger of Handler'''


        formatter = log.Formatter()
        handler = log.ConsoleHandler()
        handler.formatter = formatter
        self.logger.addHandler(handler)

        if config['global']['debug']:
            self.logger.setLevel(log.DEBUG)
        else:
            self.logger.setLevel(log.INFO)

    def __contains__(self, interface:Interface) -> bool:
        return interface in self._interfaces
    
    def __iter__(self) -> Iterator[Interface]:
        return iter(self._interfaces)
    
    def __len__(self) -> int:
        return len(self._interfaces)
    
    async def close(self):
        '''Close the handler'''
        self.logger.debug("Closing handler")
        for i in self._interfaces:
            await i.close()
        self._closed.set()

    async def close_session(self, session:Session):
        '''Close the session'''
        await session.close()
    
    def reload_commands(self) -> None:
        '''Reload commands from interfaces'''
        self.logger.debug("Reloading commands")
        self._commands.clear()
        for i in self._interfaces:
            cmds = i.commands
            for cmd in cmds:
                if cmd.expose == False:
                    continue
                cmd.extra['from'] = i
                self._commands.add(cmd)

    def reload_users(self) -> None:
        '''Reload users from interfaces'''
        self.logger.debug("Reloading users")
        # User
        self._userset.clear()
        for i in self._interfaces:
            self._userset.add(i.user)
        # Group
        groupnames:set[str] = set()
        for i in self._userset:
            for j in i.all_groups:
                groupnames.add(j)
        self._groupset.clear()
        for i in groupnames:
            _group = Group(i)
            for j in self._userset:
                if i in j.all_groups:
                    _group.add(j)
            self._groupset.add(_group)

    def reload(self):
        '''Reload commands and users from interfaces'''
        self.reload_commands()
        self.reload_users()

    def check_cmd_support(self, cmd:str) -> bool:
        '''Check whether the command is support by this handler'''
        return cmd in self._commands
    
    def get_cmd(self, cmd:str, interface:Optional[Interface] = None) -> Command:
        '''Get command by name'''
        if interface == None:
            return self._commands.get(cmd)
        else:
            if interface not in self._interfaces:
                raise error.NotFound(interface, handler=self, content='Interface Not In Handler')
            return interface.commands.get(cmd)
    
    def get_executable_cmds(self, *args, **wargs) -> Generator[Command, None, None]:
        return self._commands.get_executable(*args, **wargs)

    @overload
    async def add_interface(self, interface:Interface) -> None:
        pass

    @overload
    async def add_interface(self, *interfaces:Interface) -> None:
        pass

    async def add_interface(self, *interfaces:Interface) -> None:
        '''Add interface to the handler'''
        for i in interfaces:
            self.logger.debug("Adding interface %s - %s", i.id, i.user.name)
            if i in self._interfaces:
                raise error.Existed(i, handler=self)
            self._interfaces.add(i)
            await i.init()
        self.reload()

    @overload
    async def rm_interface(self, interface:Interface) -> None:
        pass

    @overload
    async def rm_interface(self, id:uuid.UUID) -> None:
        pass

    async def rm_interface(self, param:Interface or uuid.UUID) -> None:
        '''Remove interface from the handler'''
        if isinstance(param, Interface):
            if param not in self._interfaces:
                raise error.NotFound(param, handler=self)
            self._interfaces.remove(param)
            self.reload()
        elif isinstance(param, uuid.UUID):
            for i in self._interfaces:
                if i.id == param:
                    await i.final()
                    self._interfaces.remove(i)
                    self.reload()
                    return
            raise error.NotFound(param, handler=self)
        else:
            raise TypeError(f"Expected type Interface or uuid.UUID, got {type(param)}")
    
    def get_interface(self, id:uuid.UUID) -> Interface:
        '''Get interface by id'''
        for i in self._interfaces:
            if i.id == id:
                return i
        raise error.NotFound(id, handler=self)
    
    def get_interfaces(self, groupname:str) -> set[Interface]:
        '''Get interfaces by Group name'''
        ret = set()
        for i in self._interfaces:
            if i.user.in_group == groupname:
                ret.add(i)
        return ret
    
    @property
    def interfaces(self) -> set[Interface]:
        '''Get all interfaces'''
        return self._interfaces
    
    async def call(self, session:session.Session, message:session.Message):
        '''
        Call a command
        
        *Note*: If the destination interface is not specified, the command will be called on common command set.
        '''
        command = message.cmd
        # from_ = message.src_interface
        cmd = self.get_cmd(command, message.dest_interface)
        if cmd == None:
            raise error.CommandNotImplement(command, self)
        # if from_:
        #     if any([i in cmd.callable_groups for i in from_.user.all_groups]) == False:
        #         raise error.PermissionDenied(from_, cmd, self)
        message.dest_interface = cmd.in_interface
        return await cmd.call(session, message)

    def call_soon(self, session:session.Session, message:session.Message):
        '''
        Call a command soon
        No Result will be returned
        If the command is forced to be awaited, PermissionDenied will be raised
        '''

        # Check Premission & valify availablity
        if message.src_interface:
            if message.dest_interface:
                # Enable self interface command
                if not message.src_interface == message.dest_interface:
                    # Enable cross-interface command
                    call_groups = message.dest_interface.check_cmd_support(message.cmd).callable_groups
                    if any([i in call_groups for i in message.src_interface.user.all_groups]) == False:
                        raise error.PermissionDenied(message.cmd, interface=message.src_interface, handler=self)
            else:
                call_groups = self.get_cmd(message.cmd).callable_groups
                if any([i in call_groups for i in message.src_interface.user.all_groups]) == False:
                    raise error.PermissionDenied(message.cmd, interface=message.src_interface, handler=self)
        
        cmd = self.get_cmd(message.cmd, message.dest_interface)
        if cmd == None:
            raise error.CommandNotImplement(message.cmd, self)
        if cmd.force_await:
            raise error.PermissionDenied("Command is forced to be awaited.", cmd = cmd.cmd , dest = message.dest_interface, interface=message.src_interface, handler=self)

        async def _handle_call():
            try:
                await self.call(session, message)
            except KeyboardInterrupt:
                await self.on_keyboardinterrupt.trigger()
            except asyncio.CancelledError:
                await self.close()
                return
            except error.ConfigureMissing as e:
                self.logger.fatal("Configure missing: %s", e.configure)
                await self.on_exception.trigger(e)
            except Exception as e:
                await self.on_exception.trigger(e)
        asyncio.get_event_loop().create_task(_handle_call())

    asend = call
    '''Alias of call'''
    send = call_soon
    '''Alias of call_soon'''

    @overload
    async def new_session(self, interface:Interface) -> session.Session:
        pass

    @overload
    async def new_session(self) -> session.Session:
        pass

    async def new_session(self, 
                          interface:Optional[Interface] = None,
                          config:Optional[Config] = None) -> session.Session:
        '''
        Create a new session, will call all interfaces' session_init method
        param:
            interface: Interface, optional, the interface to set as src_interface
        '''
        ret = session.Session(self)
        self.logger.debug("Creating new session %s", ret.id)
        if interface:
            if not isinstance(interface, Interface):
                raise TypeError(f"Expected type Interface, got {type(interface)}")
            ret.src_interface = interface
        # Initialize session
        ret.config = config
        if config == None: 
            ret.config = copy.deepcopy(self.config)
            ret.config.each(
                lambda key,value: value.update(ret.config['global']),
                lambda key,value: key != 'global'
            )
        for i in self._interfaces:
            await i.session_init(ret)
        return ret
