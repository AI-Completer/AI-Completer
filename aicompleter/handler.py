'''
Handler between the interfaces
'''
import asyncio
import copy
import uuid
from typing import Generator, Iterator, Optional, overload

from aicompleter import memory

from . import error, events, interface, log, session
from .config import Config
from .interface import Command, Interface, User, Group, UserSet, GroupSet
from .interface.command import Commands
from .session.base import Session

from .namespace import Namespace

class Handler:
    '''
    Handler for AI-Completer
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
        '''Interfaces of Handler'''
        self._closed:asyncio.Event = asyncio.Event()
        '''Closed'''
        self.on_exception:events.Exception = events.Exception(Exception)
        '''Event of Exception'''
        self.on_keyboardinterrupt:events.Exception = events.Exception(KeyboardInterrupt)
        '''Event of KeyboardInterrupt'''
        self._userset:UserSet = UserSet()
        '''User Set of Handler'''
        self._groupset:GroupSet = GroupSet()
        '''Group Set of Handler'''
        self._running_sessions:set[Session] = set()
        '''Running Sessions of Handler'''
        self.on_call:events.Event = events.Event(type=events.Type.Hook)
        '''
        Event of Call, this will be triggered when a command is called
        If the event is stopped, the command will not be called
        '''

        self._namespace = Namespace(
            name='root',
            description='Root Namespace',
            config=config,
        )

        async def _default_exception_handler(e:Exception, obj:object):
            self.logger.exception(e)

        self.on_exception.add_callback(_default_exception_handler)
        
        self.on_keyboardinterrupt.add_callback(lambda e,obj:self.close())

        self.logger:log.Logger = log.getLogger('handler')
        '''Logger of Handler'''

    def _on_call(self, session:Session, message:session.Message):
        '''Call the on_call event'''
        return self.on_call.trigger(session, message)

    @property
    def commands(self):
        '''Get all commands'''
        return self._namespace.commands
    
    @property
    def config(self):
        '''Get the config'''
        return self._namespace.config

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
        for i in self._running_sessions:
            if not i.closed:
                await i.close()
        self._closed.set()

    async def close_session(self, session:Session):
        '''Close the session'''
        await session.close()
        self._running_sessions.remove(session)
        self._update_running_sessions()

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
        '''Reload users from interfaces'''
        self.reload_users()

    def check_cmd_support(self, cmd:str) -> bool:
        '''Check whether the command is support by this handler'''
        return cmd in self.commands
    
    def get_cmd(self, cmd:str, dst_interface:Optional[Interface] = None, src_interface:Optional[Interface] = None) -> Command | None:
        '''Get command by name'''
        if dst_interface == None:
            if src_interface == None:
                return next(self._namespace.getcmd(cmd), None)
            else:
                # Create a new Commands class
                ret = Commands()
                ret.add(*self._namespace.get_executable(src_interface.user))
                return ret.get(cmd, None)
        else:
            if dst_interface not in self._interfaces:
                raise error.NotFound(interface, handler=self, content='Interface Not In Handler')
            return dst_interface.commands.get(cmd, None)
    
    def get_executable_cmds(self, *args, **wargs) -> Generator[Command, None, None]:
        return self._namespace.get_executable(*args, **wargs)

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
            self._namespace.subnamespaces[i.namespace.name] = i.namespace
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
            await param.final()
            self._interfaces.remove(param)
            self._namespace.subnamespaces.pop(param.namespace.name)
            self.reload()
        elif isinstance(param, uuid.UUID):
            for i in self._interfaces:
                if i.id == param:
                    await i.final()
                    self._interfaces.remove(i)
                    self._namespace.subnamespaces.pop(i.namespace.name)
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
    
    def has_interface(self, cls:type) -> bool:
        # If cls is not a Interface type, raise TypeError
        if not issubclass(cls, Interface):
            raise TypeError(f"Expected type Interface, got {type(cls)}")
        # Check inheritance
        for i in self._interfaces:
            if isinstance(i, cls):
                return True
        return False
    
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
        cmd = self.get_cmd(command, message.dest_interface, message.src_interface)
        if cmd == None:
            raise error.CommandNotImplement(command, self)
        # if from_:
        #     if any([i in cmd.callable_groups for i in from_.user.all_groups]) == False:
        #         raise error.PermissionDenied(from_, cmd, self)
        message.session = session
        message.dest_interface = cmd.in_interface
        return await cmd.call(session, message)

    def call_soon(self, session:session.Session, message:session.Message):
        '''
        Call a command soon
        No Result will be returned
        If the command is forced to be awaited, PermissionDenied will be raised
        '''

        # Check Premission & valify availablity
        if session.closed:
            raise error.SessionClosed(session, handler=self)

        if message.src_interface:
            if message.dest_interface:
                # Enable self interface command
                if not message.src_interface == message.dest_interface:
                    # Enable cross-interface command
                    call_groups = message.dest_interface.check_cmd_support(message.cmd).callable_groups
                    if any([i in call_groups for i in message.src_interface.user.all_groups]) == False:
                        raise error.PermissionDenied(message.cmd, interface=message.src_interface, handler=self)
            else:
                if self.get_cmd(message.cmd) == None:
                    raise error.CommandNotImplement(message.cmd, self, detail = "Either the command is not implemented in the handler or the interface has no permission to call the command.")
        message.session = session
        cmd = self.get_cmd(message.cmd, message.dest_interface, message.src_interface)
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

            # This is not necessary
            self._update_running_sessions()

        asyncio.get_event_loop().create_task(_handle_call())

    asend = call
    '''Alias of call'''
    send = call_soon
    '''Alias of call_soon'''

    def _update_running_sessions(self):
        for i in self._running_sessions:
            if i.closed:
                self._running_sessions.remove(i)

    async def new_session(self, 
                          interface:Optional[Interface] = None,
                          config:Optional[Config] = None,
                          memoryConfigure:Optional[memory.MemoryConfigure] = None) -> session.Session:
        '''
        Create a new session, will call all interfaces' session_init method
        :param interface:Interface, optional, the interface to set as src_interface
        :param config:Config, optional, the config to set as session.config
        :param memoryConfigure:MemoryConfigure, optional, the memory configure to set as session.memoryConfigure
        '''
        ret = session.Session(self, memoryConfigure)
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
        self._running_sessions.add(ret)
        return ret

__all__ = (
    'Handler',
)
