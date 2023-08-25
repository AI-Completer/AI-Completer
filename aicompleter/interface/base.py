'''
Base Objects for Interface of AutoDone-AI
'''
import copy
import json
import os
import uuid
from typing import Coroutine, Optional, Self, TypeVar, Union, overload
import asyncio

import attr

from .. import config, error, handler, log, session, utils
from ..common import AsyncLifeTimeManager, JSONSerializable
from ..config import Config, ConfigModel
from ..session import Session
from ..namespace import Namespace, BaseNamespace
from ..utils import EnhancedDict
from .command import Command, Commands

Handler = TypeVar('Handler', bound='handler.Handler')

@attr.dataclass(hash=False)
class User(JSONSerializable):
    '''User'''
    name:str = attr.ib(default="", kw_only=False)
    '''
    Name of the user
    If the name is empty, the user will be assigned a name by the handler
    '''
    description:Optional[str] = attr.ib(default=None, kw_only=False)
    '''Description of the user'''
    
    id:uuid.UUID = attr.ib(factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID), kw_only=True)
    '''ID of the user'''
    in_group:str = attr.ib(default="",on_setattr=lambda self, attr, value: self.all_groups.add(value), kw_only=True)
    '''Main Group that the user in'''
    all_groups:set[str] = attr.ib(factory=set, kw_only=True)
    '''Groups that the user in'''
    support:set[str] = attr.ib(factory=set, kw_only=True)
    '''Supports of the user'''

    @property
    def support_text(self) -> bool:
        '''Support text'''
        return "text" in self.support
    
    @property
    def support_image(self) -> bool:
        '''Support image'''
        return "image" in self.support
    
    @property
    def support_audio(self) -> bool:
        '''Support audio'''
        return "audio" in self.support
    
    def __hash__(self) -> int:
        return hash(self.id) + hash(self.name)
    
    def __attrs_post_init__(self):
        if self.in_group not in self.all_groups:
            self.all_groups.add(self.in_group)

class Group:
    '''
    Group
    include:
    - User
    - System
    - Agent
    - ...
    Like Linux User Group
    '''
    def __init__(self, name:str) -> None:
        self.name:str = name
        '''Name of the group'''
        self._users:set[User] = set()
        '''Users in the group'''

    def __contains__(self, user:User) -> bool:
        return user in self._users
    
    def __iter__(self):
        return iter(self._users)
    
    def add(self, user:User) -> None:
        '''Add user to the group'''
        for u in self._users:
            if u.name == user.name:
                if u != user:
                    raise error.Existed("User %s already in group %s" % (user.name, self.name))
        self._users.add(user)
            
    def remove(self, user:User):
        '''Remove user from the group'''
        self._users.remove(user)

    def clear(self):
        '''Clear the group'''
        self._users.clear()

    def extend(self, users:set[User]):
        '''Extend the group'''
        for i in users:
            self.add(i)

    def __repr__(self) -> str:
        return "<Group %s>" % self.name
    
    def __str__(self) -> str:
        return self.name
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    @property
    def users(self):
        '''Users in the group'''
        return self._users
    
class UserSet(JSONSerializable):
    '''Set of User'''
    def __init__(self) -> None:
        self._set:set[User] = set()
        '''Set of User'''
    
    @overload
    def __contains__(self, user:User) -> bool:
        pass

    @overload
    def __contains__(self, name:str) -> bool:
        pass

    def __contains__(self, user:User | str) -> bool:
        if isinstance(user, User):
            return user in self._set
        else:
            for i in self._set:
                if i.name == user:
                    return True
            return False
    
    def has(self, name:str):
        '''Check whether the set has the user by name'''
        for i in self._set:
            if i.name == name:
                return True
        return False
    
    def add(self, user:User):
        '''Add user to the set'''
        if self.has(user.name):
            raise error.Existed("User %s already in the set" % user.name)
        self._set.add(user)

    @overload
    def remove(self, user:User) -> None:
        pass

    @overload
    def remove(self, name:str) -> None:
        pass

    def remove(self, user:User|str):
        '''Remove user from the set'''
        if user not in self:
            raise error.NotFound("User %s not found in the set" % user)
        if isinstance(user, User):
            self._set.remove(user)
        else:
            for i in self._set:
                if i.name == user:
                    self._set.remove(i)
                    break

    def get(self, name:str):
        '''Get user by name'''
        for i in self._set:
            if i.name == name:
                return i
        return None

    def __iter__(self):
        return iter(self._set)
    
    def clear(self):
        '''Clear the set'''
        self._set.clear()
    
class GroupSet(JSONSerializable):
    '''Set of Group'''
    def __init__(self) -> None:
        self._set:set[Group] = set()
        '''Set of Group'''

    @overload
    def __contains__(self, group:Group) -> bool:
        pass

    @overload
    def __contains__(self, name:str) -> bool:
        pass

    def __contains__(self, group:Group | str) -> bool:
        if isinstance(group, Group):
            return group in self._set
        else:
            for i in self._set:
                if i.name == group:
                    return True
            return False
    
    def has(self, name:str):
        '''Check whether the set has the group by name'''
        for i in self._set:
            if i.name == name:
                return True
        return False
    
    def add(self, group:Group):
        '''Add group to the set'''
        if self.has(group.name):
            raise error.Existed("Group %s already in the set" % group.name)
        self._set.add(group)

    @overload
    def remove(self, group:Group) -> None:
        pass

    @overload
    def remove(self, name:str) -> None:
        pass

    def remove(self, group:Group|str):
        '''Remove group from the set'''
        if group not in self:
            raise error.NotFound("Group %s not found in the set" % group)
        if isinstance(group, Group):
            self._set.remove(group)
        else:
            for i in self._set:
                if i.name == group:
                    self._set.remove(i)
                    break

    def get(self, name:str):
        '''Get group by name'''
        for i in self._set:
            if i.name == name:
                return i
        return None
    
    def __iter__(self):
        return iter(self._set)
    
    def clear(self):
        '''Clear the set'''
        self._set.clear()

    def finduser(self, username:str):
        '''Find user by name'''
        for i in self._set:
            for j in i:
                if j.name == username:
                    return j
        return None

class Interface(AsyncLifeTimeManager):
    '''Interface of AI Completer'''
    cmdreg = Commands()
    '''
    Command Register
    
    Add Command to this class to register a command
    '''
    configFactory:type[Config] = Config
    '''
    Configure Factory, this factory will be used to create a configure for the interface
    '''
    dataFactory:type[utils.EnhancedDict] = utils.EnhancedDict
    '''
    Data Factory, this factory will be used to create a data class for the interface
    '''
    namespace: Optional[BaseNamespace] = None
    '''
    Base Namespace, this namespace will be used to create a namespace for the interface
    '''

    def __init__(self, 
                 namespace:Optional[str] = None, 
                 user:Optional[User] = None,
                 id:uuid.UUID = uuid.uuid4(), 
                 config: config.Config = config.Config()):
        
        super().__init__()
        self._user = user
        '''Character of the interface'''
        utils.typecheck(id, uuid.UUID)
        self._id:uuid.UUID = id
        '''ID'''
        
        if namespace is None:
            if hasattr(type(self), "namespace") and isinstance(type(self).namespace, BaseNamespace):
                self.namespace.__dict__.update(attr.asdict(type(self).namespace))
            else:
                raise error.InvalidArgument("namespace is not specified")
        else:
            self.namespace:Namespace = Namespace(
                name=namespace,
                description="Interface %s" % str(type(self).__qualname__),
                config=config,
                data=self.dataFactory(),
            )
        self.loop:Optional[asyncio.AbstractEventLoop] = None

        self.logger:log.Logger = log.getLogger("interface", [self.namespace.name])
        '''Logger of Interface'''
        for cls in (*self.__class__.__bases__, self.__class__):
            if issubclass(cls, Interface):
                if hasattr(cls, "cmdreg") and isinstance(cls.cmdreg, Commands):
                    for cmd in cls.cmdreg:
                        newcmd = copy.copy(cmd)
                        newcmd.in_interface = self
                        # if is a class method, bind the method to the instance
                        if not hasattr(newcmd.callback, "__self__") and '.' in newcmd.callback.__qualname__:
                            if self.__class__.__name__ == newcmd.callback.__qualname__.rsplit('.', maxsplit=2)[-2]:
                                newcmd.callback = newcmd.callback.__get__(self, self.__class__)
                        self.commands.add(newcmd)

        self.__inited = False

    @property
    def data(self) -> EnhancedDict:
        '''Data of the interface'''
        return self.namespace.data
    
    @property
    def commands(self) -> Commands:
        '''Commands of the interface'''
        return self.namespace.commands
    
    @property
    def config(self) -> Config:
        '''Config of the interface'''
        return self.namespace.config

    @property
    def user(self) -> User:
        '''
        Character of the interface
        (Read-only)
        :rtype: User
        '''
        return self._user

    @property
    def id(self):
        '''ID of the interface'''
        return self._id

    def check_cmd_support(self, cmd:str) -> Command:
        '''Check whether the command is support by this interface'''
        for i in self.commands:
            if i.cmd == cmd:
                return i
            for j in i.alias:
                if j == cmd:
                    return i
        return None
    
    async def init(self, in_handler:Handler) -> Coroutine[None, None, None]:
        '''
        Initial function for Interface

        This method will be called when the interface is initializing,

        *Note*: The method will be called even if this method is inherited or removd from the subclass
        '''
        self.logger.debug("Interface %s initializing" % self.id)
        self.loop = in_handler._loop
        self.__inited = True

    async def final(self) -> Coroutine[None, None, None]:
        '''
        Finial function for Interface
        
        This method will be called when the interface is finalizing,

        *Note*: The method will be called even if this method is inherited or removd from the subclass
        '''
        self.logger.debug("Interface %s finalizing" % self.id)
    
    async def _invoke_init(self, in_handler: Handler):
        '''
        Invoke the init function of the interface
        '''
        # find all init functions from the mro
        inits = []
        for func in utils.get_inherit_methods(self.__class__, "init"):
            if callable(func):
                inits.append(func)
        # invoke all init functions
        for i in inits:
            params = utils.appliable_parameters(i, {
                'in_handler': in_handler,
                'handler': in_handler
            })
            await i(self, **params)

    async def _invoke_final(self, in_handler: Handler):
        '''
        Invoke the final function of the interface
        '''
        # find all final functions from the mro
        finals = []
        for func in utils.get_inherit_methods(self.__class__, "final"):
            if callable(func):
                finals.append(func)
        finals.reverse()
        # invoke all final functions, from the last to the first
        for i in finals:
            params = utils.appliable_parameters(i, {
                'in_handler': in_handler,
                'handler': in_handler
            })
            await i(self, **params)

    async def session_init(self):
        '''
        Initial function for Session
        
        This method can be inherited with arguments
        - session:Session (optional), the session to init

        ::
            >>> async def session_init(self, session:Session):
            ...     # Do something
        ::
        '''
        pass

    async def session_final(self):
        '''
        Finial function for Session
        
        This method can be inherited with arguments
        - session:Session (optional), the session to final

        ::
            >>> async def session_final(self, session:Session):
            ...     # Do something
        '''
        pass

    async def _invoke_session_init(self, session: Session):
        '''
        Invoke the session init function of the interface
        '''
        session_inits = []
        for func in utils.get_inherit_methods(self.__class__, "session_init"):
            if callable(func):
                session_inits.append(func)
        raw_data = self.getdata(session)
        raw_config = self.getconfig(session)
        for i in session_inits:
            params = utils.appliable_parameters(i, {
                'session': session,
                'data': raw_data,
                'config': raw_config
            })
            await i(self, **params)
        self.setdata(session, raw_data)
        self.setconfig(raw_config, session)

    async def _invoke_session_final(self, session: Session):
        '''
        Invoke the session final function of the interface
        '''
        session_finals = []
        for func in utils.get_inherit_methods(self.__class__, "session_final"):
            if callable(func):
                session_finals.append(func)
        session_finals.reverse()
        raw_data = self.getdata(session)
        raw_config = self.getconfig(session)
        for i in session_finals:
            params = utils.appliable_parameters(i, {
                'session': session,
                'data': raw_data,
                'config': raw_config
            })
            await i(self, **params)
        self.setdata(session, raw_data)
        self.setconfig(raw_config, session)

    @overload
    def getconfig(self, session:session.Session) -> Config:
        pass

    @overload
    def getconfig(self, session:None, configFactory:type[Config]) -> Config:
        pass

    def getconfig(self, session:Optional[session.Session] = None, configFactory: type[Config] = None) -> Config:
        '''
        Get the config of the interface
        :param session: Session
        :param configFactory: Config Factory, if specified, will create a new config by the factory

        :return: Session Config, if session is None, return interface config
        '''
        # There is a config conflict when using mutable interface
        ret = (configFactory or self.configFactory)()
        ret.update(session.config['global'])
        ret.update(self.namespace.config)
        if session:
            ret.update(session.config[self.namespace.name])
        return ret
    
    def setconfig(self, config: Config, session:Optional[session.Session] = None):
        '''
        Set the config of the interface
        :param config: Config, the config to be set
        :param session: Session, if specified, the session data will be modified but not interface
        '''
        if isinstance(config, ConfigModel):
            config = config.__wrapped__
        if session != None:
            session.config[self.namespace.name] = config
        else:
            self.namespace.config = config
    
    def getdata(self, session:session.Session) -> EnhancedDict:
        '''
        Get the data of the interface
        :param session: Session
        '''
        ret = session.data[self.id.hex]
        if type(ret) != self.dataFactory:
            ret = session.data[self.id.hex] = self.dataFactory(ret)
        return ret
    
    def setdata(self, session:session.Session, data: EnhancedDict):
        '''
        Set the data of the interface
        :param session: Session
        :param data: Data
        '''
        session.data[self.id.hex] = data

    async def call(self, session:session.Session, message:session.Message):
        '''
        Call the command

        :param session: Session
        :param message: Message

        When no callback is found, use this method to call the command
        '''
        raise NotImplementedError("Interface.call() is not implemented")

    def getStorage(self, session:session.Session) -> Optional[dict]:
        '''
        Get the Storage of the interface (if any)

        If possible, use save_session alternatively

        :param session: Session
        :return: Storage, if there is nothing to store, return None
        '''
        return None
    
    def setStorage(self, session:session.Session, data:dict):
        '''
        Set the Storage of the interface (if any)

        If possible, use load_session alternatively

        :param session: Session
        '''
        pass

    def save_session(self, path:str, session:session.Session):
        with open(path, 'w') as f:
            json.dump(self.getStorage(session) or {}, f)

    def load_session(self, path:str, session:session.Session):
        with open(path, 'r') as f:
            self.setStorage(session, json.load(f))

    def rename_cmd(self, old:str, new:str):
        '''
        Rename a command
        This method is used to handle a conflict of command name
        :param old: Old name
        :param new: New name
        '''
        for cmd in self.commands:
            if cmd.cmd == old:
                cmd.cmd = new
            if new in cmd.alias:
                cmd.alias.remove(new)
