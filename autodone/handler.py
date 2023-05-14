'''
Handler between the interfaces
'''
import asyncio
import uuid
from typing import Awaitable, Iterable, Iterator, Optional, overload

from . import error, events, interface, log, session
from .config import Config
from .interface.base import Command, Interface, Role
from .interface.command import CommandSet
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
        self._commands:CommandSet = CommandSet()
        # self._call_queues:list[tuple[session.Session, session.Message]] = []
        self._closed:asyncio.Event = asyncio.Event()
        '''Closed'''
        self.config:Config = config
        '''Config of Handler'''
        self.global_config:Config = config['global']
        '''Global Config of Handler'''
        self.on_exception:events.Exception = events.Exception(Exception)
        '''Event of Exception'''
        self.on_keyboardinterrupt:events.Exception = events.Exception(KeyboardInterrupt)
        '''Event of KeyboardInterrupt'''

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

    def check_cmd_support(self, cmd:str) -> bool:
        '''Check whether the command is support by this handler'''
        return cmd in self._commands
    
    def get_cmd(self, cmd:str, interface:Optional[Interface] = None) -> Command:
        '''Get command by name'''
        if interface == None:
            return self._commands.get(cmd)
        else:
            return interface.commands.get(cmd)
    
    def get_cmds_by_role(self, role:Role) -> list[Command]:
        '''Get commands by role'''
        return self._commands.get_by_role(role)

    @overload
    async def add_interface(self, interface:Interface) -> None:
        pass

    @overload
    async def add_interface(self, *interfaces:Interface) -> None:
        pass

    async def add_interface(self, *interfaces:Interface) -> None:
        '''Add interface to the handler'''
        for i in interfaces:
            self.logger.debug("Adding interface %s - %s", i.id, i.character.name)
            if i in self._interfaces:
                raise error.Existed(i, handler=self)
            self._interfaces.add(i)
            i.config = self.config['global']
            i.config.update(self.config['interface'][i.namespace])
            await i.init()
        self.reload_commands()

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
            self.reload_commands()
        elif isinstance(param, uuid.UUID):
            for i in self._interfaces:
                if i.id == param:
                    await i.final()
                    self._interfaces.remove(i)
                    self.reload_commands()
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
    
    def get_interfaces(self, role:Role) -> set[Interface]:
        '''Get interfaces by role'''
        ret = set()
        for i in self._interfaces:
            if i.role == role:
                ret.add(i)
        return ret
    
    @property
    def interfaces(self) -> set[Interface]:
        '''Get all interfaces'''
        return self._interfaces
    
    async def call(self, session:session.Session, message:session.Message) -> None:
        '''
        Call a command
        
        *Note*: If the destination interface is not specified, the command will be called on common command set.
        '''
        command = message.cmd
        from_ = message.src_interface
        cmd = self.get_cmd(command, message.dest_interface)
        if cmd == None:
            raise error.CommandNotImplement(command, self)
        if from_:
            if from_.character.role not in cmd.callable_roles:
                raise error.PermissionDenied(from_, cmd, self)
        message.dest_interface = cmd.in_interface
        await cmd.call(session, message)

    def call_soon(self, session:session.Session, message:session.Message) -> None:
        '''Call a command soon'''
        async def _handle_call():
            try:
                await self.call(session, message)
            except KeyboardInterrupt:
                self.on_keyboardinterrupt.trigger()
            except asyncio.CancelledError:
                await self.close()
                return
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

    async def new_session(self, interface:Optional[Interface] = None) -> session.Session:
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
        for i in self._interfaces:
            await i.session_init(ret)
        return ret
