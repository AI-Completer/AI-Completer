'''
Handler between the interfaces
'''
import asyncio
import copy
import functools
import importlib
import json
import uuid
from typing import Any, Coroutine, Generator, Iterator, Optional, Self, overload

from . import utils
from .utils.storage import StorageManager
from .common import AsyncLifeTimeManager, Saveable

from . import error, events, interface, log, session
from .config import Config
from .interface import Command, Interface, User, Group, UserSet, GroupSet
from .interface.command import Commands
from .session.base import Session

from .namespace import Namespace
from .utils.special import getcallercommand

class Handler(AsyncLifeTimeManager, Saveable):
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

    @overload
    def __init__(self, config:Config, loop:asyncio.AbstractEventLoop) -> None:
        pass

    def __init__(self, config:Optional[Config] = Config(), loop:Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__()
        self._interfaces:list[Interface] = []
        '''Interfaces of Handler'''
        self.on_exception:events.Exception = events.Exception(Exception)
        '''Event of Exception'''
        self.on_keyboardinterrupt:events.Exception = events.Exception(KeyboardInterrupt)
        '''Event of KeyboardInterrupt'''
        self._userset:UserSet = UserSet()
        '''User Set of Handler'''
        self._groupset:GroupSet = GroupSet()
        '''Group Set of Handler'''
        self._running_sessions:list[Session] = []
        '''Running Sessions of Handler'''

        self.logger:log.Logger = log.getLogger('handler')
        '''Logger of Handler'''

        if loop == None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        else:
            self._loop = loop
        
        self._namespace = Namespace(
            name='root',
            description='Root Namespace',
            config=config,
        )

        async def _default_exception_handler(e:Exception, obj:object):
            self.logger.exception(e)

        self.on_exception.add_callback(_default_exception_handler)
        
        self.on_keyboardinterrupt.add_callback(lambda e,obj:self.close())

    def _on_call(self, session:Session, message:session.Message):
        '''Call the on_call event'''
        return session.on_call.trigger(session, message)

    @property
    def commands(self):
        '''Get all commands'''
        return self._namespace.get_executable()
    
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
        for i in self._running_sessions:
            if not i.closed:
                await i.close()
        for i in self._interfaces:
            await i._invoke_final(self)
            await i.close()
        await super().close()

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
            if i.user.name not in self._userset:
                self._userset.add(i.user)
            elif i.user != self._userset[i.user.name]:
                raise error.Conflict('interface user conflict', name=i.user.name, interface=self)
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
    
    def assign_user(self, 
                    description:Optional[str] = None, 
                    in_group:Optional[str] = "",
                    all_groups:Optional[set[str]] = set(),
                    support:Optional[set[str]] = set()) -> User:
        '''
        Assign a new user
        '''
        def _random_name():
            import random
            import string
            return ''.join(random.choice(string.ascii_letters) for i in range(10))
        while True:
            name = _random_name()
            if name not in self._userset:
                break
        return User(
            name=name,
            description=description,
            in_group=in_group,
            all_groups=all_groups,
            support=support,
        )

    @overload
    async def add_interface(self, interface:Interface) -> None:
        pass

    @overload
    async def add_interface(self, *interfaces:Interface) -> None:
        pass

    async def add_interface(self, *interfaces:Interface) -> None:
        '''Add interface to the handler'''
        for i in interfaces:
            utils.typecheck(i, Interface)
            # Assign user if not assigned
            if i._user == None:
                i._user = self.assign_user()
            if i._user.name == "":
                i._user = self.assign_user(
                    description=i._user.description,
                    in_group=i._user.in_group,
                    all_groups=i._user.all_groups,
                    support=i._user.support,
                )
            
            self.logger.debug("Adding interface %s - %s", i.id, i.user.name)
            if i in self._interfaces:
                raise error.Existed(i, handler=self)
            self._interfaces.append(i)
            if i.namespace.name in self._namespace.subnamespaces:
                # Discuss whether the namespace is same
                if not i.namespace == self._namespace.subnamespaces[i.namespace.name]:
                    raise error.NamespaceConflict(i.namespace, "There is a namespace existed with the same name, but not the same content."\
                            "Is there two conflicted name?", existed_namespace=self._namespace.subnamespaces[i.namespace.name])
                # Normal case, in this, there are two or more interfaces in same type added to this handler
            else:
                self._namespace.subnamespaces[i.namespace.name] = i.namespace
        for i in interfaces:
            await i._invoke_init(self)
        self.reload()

    @overload
    async def rm_interface(self, interface:Interface) -> None:
        pass

    @overload
    async def rm_interface(self, id:uuid.UUID) -> None:
        pass

    async def rm_interface(self, param:Interface or uuid.UUID) -> None:
        '''Remove interface from the handler'''
        def _rm_namespace(name):
            for sub in self._namespace.subnamespaces.values():
                if sub.name == name:
                    break
            else:
                # remove
                del self._namespace.subnamespaces[name]
        if isinstance(param, Interface):
            if param not in self._interfaces:
                raise error.NotFound(param, handler=self)
            await param.final()
            self._interfaces.remove(param)
            _rm_namespace(param.namespace.name)
            self.reload()
        elif isinstance(param, uuid.UUID):
            for i in self._interfaces:
                if i.id == param:
                    params = utils.appliable_parameters(i.final, {
                        'in_handler': self,
                        'handler': self,
                    })
                    await i.final(**params)
                    self._interfaces.remove(i)
                    _rm_namespace(i.namespace.name)
                    self.reload()
                    return
            raise error.NotFound(param, handler=self)
        else:
            raise TypeError(f"Expected type Interface or uuid.UUID, got {type(param)}")
    
    @overload
    def get_interface(self, id:uuid.UUID) -> Interface:
        ...

    @overload
    def get_interface(self, groupname:str) -> list[Interface]:
        ...

    @overload
    def get_interface(self, interface:Interface) -> Interface:
        ...

    @overload
    def get_interface(self, cls:type) -> list[Interface]:
        ...
    
    def get_interface(self, param: uuid.UUID | str):
        '''
        Get interfaces which match the condition
        :param id:uuid.UUID, the id of the interface
        :param groupname:str, the groupname of the interface
        :param interface:Interface, the interface
        :param cls:type, the type of the interface
        '''
        if isinstance(param, uuid.UUID):
            for i in self._interfaces:
                if i.id == param:
                    return i
            raise error.NotFound(param, handler=self)
        elif isinstance(param, str):
            ret = []
            for i in self._interfaces:
                if i.user.in_group == param:
                    ret.append(i)
            return ret
        elif isinstance(param, Interface):
            if param in self._interfaces:
                return param
            raise error.NotFound(param, handler=self)
        elif issubclass(param, Interface):
            ret = []
            for i in self._interfaces:
                if isinstance(i, param):
                    ret.append(i)
            return ret
        else:
            raise TypeError(f"Expected type Interface or uuid.UUID, got {type(param)}")
    
    def has_interface(self, cls:type) -> bool:
        # If cls is not a Interface type, raise TypeError
        if not issubclass(cls, Interface):
            raise TypeError(f"Expected type Interface, got {type(cls)}")
        # Check inheritance
        for i in self._interfaces:
            if isinstance(i, cls):
                return True
        return False
    
    def require_interface(self, cls:type[Interface], user:Optional[User] = None) -> Interface:
        if not issubclass(cls, Interface):
            raise TypeError(f"Expected type Interface, got {type(cls)}")
        for cmd in self._namespace.get_executable(user):
            cmd:Command
            if cmd.in_interface:
                if isinstance(cmd.in_interface, cls):
                    return cmd.in_interface
        # If no command found, try to find interface
        for interface in self._interfaces:
            if isinstance(interface, cls):
                if interface.commands.empty():
                    # This is right, because no command is executable and therefor no permission is required
                    return interface
        raise error.NotFound(f"Require Interface {cls}, but not found or permission required" + (f" with user {user.name}" if user else ""))
    
    @property
    def interfaces(self) -> list[Interface]:
        '''Get all interfaces'''
        return self._interfaces
    
    def call(self, session:session.Session, message:session.Message) -> Coroutine[None, None, Any]:
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

        if not message._check_cache.get('src_interface', False): 
            if message.src_interface is None:
                callercommand = getcallercommand(commands=self._namespace.get_executable())
                if callercommand:
                    message.src_interface = callercommand.in_interface
            message._check_cache['src_interface'] = True

        return cmd.call(session, message)

    def call_soon(self, session:session.Session, message:session.Message):
        '''
        Call a command soon
        No Result will be returned
        If the command is forced to be awaited, PermissionDenied will be raised
        '''

        # Check Premission & valify availablity
        if session.closed:
            raise error.SessionClosed(session, handler=self)
        
        if not message._check_cache.get('src_interface', False): 
            if message.src_interface == None:
                callercommand = getcallercommand(commands=self._namespace.get_executable())
                if callercommand:
                    message.src_interface = callercommand.in_interface
            message._check_cache['src_interface'] = True
        
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

        async def _handle_call():
            try:
                await cmd.call(session, message)
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

        self._loop.create_task(_handle_call())

    def _update_running_sessions(self):
        for i in self._running_sessions:
            if i.closed:
                self._running_sessions.remove(i)

    async def new_session(self, 
                          config:Optional[Config] = None) -> session.Session:
        '''
        Create a new session, will call all interfaces' session_init method
        :param interface:Interface, optional, the interface to set as src_interface
        :param config:Config, optional, the config to set as session.config
        :param memoryConfigure:MemoryConfigure, optional, the memory configure to set as session.memoryConfigure
        '''
        ret = session.Session(self)
        self.logger.debug("Creating new session %s", ret.id)
        # Initialize session
        ret.config = config
        if config == None:
            ret.config = copy.deepcopy(self.config)
            ret.config.each(
                lambda key,value: value.update(ret.config['global']),
                lambda key,value: key != 'global'
            )
        try:
            await ret._init_session()
        except Exception as e:
            self.logger.critical("Unexception: %s", e)
            raise e
        self._running_sessions.append(ret)
        return ret
    
    def loadSession(self, data:dict[str, Any]) -> session.Session:
        '''Load session'''
        self.logger.debug("Loading session %s", data['id'])
        ret = session.Session(self)
        ret.config = Config.__deserialize__(data['config'])
        ret._id = uuid.UUID(data['id'])
        for i in data['storage']:
            for j in self._interfaces:
                if j.id.hex == i['id']:
                    j.setStorage(ret, i['data'])
                    break
            else:
                raise error.NotFound("Interface %s not found" % i['id'], handler=self)
        self._running_sessions.append(ret)
        return ret
    
    def getstate(self):
        '''
        Get state of handler

        This method may be removed in the future
        '''
        return {
            'interfaces': [
                {
                    'id': i.id.hex,
                    'module': i.__module__,
                    'class': i.__class__.__qualname__,
                    'config': dict(i.config),
                    'user': i.user.__serialize__(),
                    'commands': [{
                        'name': cmd.cmd,
                        'callable_groups': list(cmd.callable_groups),
                    } for cmd in i.commands]
                } for i in self._interfaces
            ]
        }
    
    def setstate(self, state:dict[str, Any]):
        '''
        Set state of handler
        
        This method may be removed in the future
        '''
        # Require preload interfaces, because the interface init method varies
        self.logger.debug("Set state of handler")
        _loaded_interfaces = []
        def get_interface(type_: type[Interface]):
            for i in self._interfaces:
                if i not in _loaded_interfaces:
                    if i.__class__ == type_:
                        _loaded_interfaces.append(i)
                        return i
            return None
        for i in state['interfaces']:
            module = importlib.import_module(i['module'])
            for name in i['class'].split('.'):
                module = getattr(module, name)
            cls:type[Interface] = module
            if not issubclass(cls, Interface):
                raise TypeError(f"Expected type Interface, got {type(cls)}")
            # Check if the interface is already loaded
            _inter = get_interface(cls)
            if _inter:
                _inter.namespace.config = Config(i['config'])
                _inter._user = User.__deserialize__(i['user'])
                _inter._id = uuid.UUID(i['id'])
                assert _inter in self._interfaces, "Interface not in handler"
            else:
                kwparams = utils.appliable_parameters(cls.__init__,{
                    'config': Config.__deserialize__(i['config']),
                    'user': User.__deserialize__(i['user']),
                    'id': uuid.UUID(i['id']),
                })
                try:
                    _inter = cls(**kwparams)
                except TypeError as e:
                    self.logger.error("Exception: %s", e)
                    self.logger.fatal("Failed to initialize interface %s(%s)", i['id'], cls.__name__)
                    raise e
                _inter._user = User.__deserialize__(i['user'])
                self._interfaces.append(_inter)
            for cmd in i.get('commands', []):
                if cmd['name'] not in _inter.commands:
                    raise error.NotFound(cmd['name'], interface=_inter, handler=self)
                _inter.commands[cmd['name']].callable_groups = set(cmd['callable_groups'])

    def save(self, path:str | StorageManager):
        '''Save handler to path'''
        if isinstance(path, str):
            path = StorageManager(path)
        intmeta = self.getstate()
        with open(path.alloc_file('intmeta'), 'w') as f:
            json.dump(intmeta, f)
        with open(path.alloc_file('config'), 'w') as f:
            json.dump(self.config, f)
        sessions = path.alloc_storage('sessions')
        for i in self._running_sessions:
            session_storage = sessions.alloc_storage(i.id.hex)
            i.save(session_storage, True)
        sessions.save()
        path.save()
        self.logger.info("Handler saved to %s", path.path)

    @classmethod
    def load(cls, path:str | StorageManager, prehandler: Optional[Self] = None):
        '''Load handler from path'''
        if isinstance(path, str):
            path = StorageManager.load(path)
        with open(path['intmeta'].path, 'r') as f:
            intmeta = json.load(f)
        with open(path['config'].path, 'r') as f:
            config = Config(json.load(f))
        if prehandler:
            ret = prehandler
            ret._namespace.config = config
        else:
            ret = cls(config)
        ret.setstate(intmeta)
        sessions = StorageManager.load(path['sessions'].path)
        for i in sessions:
            session_storage = sessions[i.mark]
            ret._running_sessions.append(Session.load(
                StorageManager.load(session_storage.path), ret))
        return ret

__all__ = (
    'Handler',
)
