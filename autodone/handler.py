'''
Handler between the interfaces
'''
from typing import Iterable, Iterator, overload
from autodone.interface.base import Interface, Command, Role
from autodone.interface.command import CommandSet
import session
import asyncio
import uuid
import error

class Handler:
    '''
    Handler for AutoDone-AI
    The handler will transfer various information between Interfaces, 
    enabling interaction among person, AI and system.
    '''
    def __init__(self) -> None:
        self._interfaces:set[Interface] = set()
        self._commands:CommandSet = CommandSet()
        self._call_queues:list[tuple[session.Session, session.Message]] = []
        self.closed:bool = False

        async def queue_check():
            await self.init_interfaces()
            while True:
                if self.closed:
                    return
                if len(self._call_queues) > 0:
                    session, message = self._call_queues.pop(0)
                    await self.call(session, message)
                await asyncio.sleep(0.1)

        asyncio.get_event_loop().create_task(queue_check())

    def __contains__(self, interface:Interface) -> bool:
        return interface in self._interfaces
    
    def __iter__(self) -> Iterator[Interface]:
        return iter(self._interfaces)
    
    def __len__(self) -> int:
        return len(self._interfaces)
    
    def reload_commands(self) -> None:
        '''Reload commands from interfaces'''
        self._commands.clear()
        for i in self._interfaces:
            cmds = i.commands
            for cmd in cmds:
                if cmd.expose == False:
                    continue
                cmd.extra['from'] = i
                self._commands.add(cmd)

    def check_cmd_support(self, cmd:str) -> Command:
        '''Check whether the command is support by this handler'''
        return cmd in self._commands
    
    def get_cmds_by_role(self, role:Role) -> list[Command]:
        '''Get commands by role'''
        return self._commands.get_by_role(role)

    @overload
    def add_interface(self, interface:Interface) -> None:
        pass

    @overload
    def add_interface(self, *interfaces:Interface) -> None:
        pass

    def add_interface(self, *interfaces:Interface) -> None:
        '''Add interface to the handler'''
        for i in interfaces:
            if i in self._interfaces:
                raise error.Existed(i, handler=self)
            self._interfaces.add(i)

    @overload
    def rm_interface(self, interface:Interface) -> None:
        pass

    @overload
    def rm_interface(self, id:uuid.UUID) -> None:
        pass

    def rm_interface(self, param:Interface or uuid.UUID) -> None:
        '''Remove interface from the handler'''
        if isinstance(param, Interface):
            if param not in self._interfaces:
                raise error.NotFound(param, handler=self)
            self._interfaces.remove(param)
            self.reload_commands()
        elif isinstance(param, uuid.UUID):
            for i in self._interfaces:
                if i.id == param:
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
    
    async def call(self, session:session.Session, message:session.Message) -> None:
        '''Call a command'''
        command = message.cmd
        from_ = message.src_interface
        cmd = self.check_cmd_support(command)
        if cmd == None:
            raise error.CommandNotImplement(command, self)
        if from_.character.role not in cmd.callable_roles:
            raise error.PermissionDenied(from_, cmd, self)
        if from_ not in cmd.callable_roles:
            raise error.PermissionDenied(from_, cmd, self)
        message.dest_interface = cmd.in_interface
        await cmd.call(session, message)

    def call_soon(self, session:session.Session, message:session.Message) -> None:
        '''Call a command soon'''
        self._call_queues.append((session, message))

    asend = call
    '''Alias of call'''
    send = call_soon
    '''Alias of call_soon'''

    @overload
    def new_session(self, interface:Interface) -> session.Session:
        pass

    @overload
    def new_session(self) -> session.Session:
        pass

    def new_session(self, interface:Interface|None = None) -> session.Session:
        '''Create a new session'''
        ret = session.Session(self)
        if interface:
            if not isinstance(interface, Interface):
                raise TypeError(f"Expected type Interface, got {type(interface)}")
            ret.src_interface = interface
        return ret

    async def init_interfaces(self):
        '''Init interfaces'''
        for i in self._interfaces:
            await i.init()
