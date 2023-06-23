'''
Base Objects for Interface of AutoDone-AI
'''
import os
import uuid
from abc import abstractmethod
from typing import Optional, overload

import attr

import aicompleter.session as session
from aicompleter import error, log

from .command import Command, Commands

@attr.s(auto_attribs=True, kw_only=True, hash=False)
class User:
    '''User'''
    name:str = ""
    '''Name of the user'''
    id:uuid.UUID = uuid.uuid4()
    '''ID of the user'''
    description:Optional[str] = None
    '''Description of the user'''
    in_group:str = attr.ib(default="",on_setattr=lambda self, attr, value: self.all_groups.add(value))
    '''Main Group that the user in'''
    all_groups:set[str] = set()
    '''Groups that the user in'''
    support:set[str] = set()
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
    
class UserSet:
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
    
class GroupSet:
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

class _Interface:
    '''Interface of AI-Completer'''
    namespace:str = ""
    def __new__(self, *args, **kwargs):
        raise DeprecationWarning("This Interface Class is deprecated, use aicompleter.interface.Interface instead")
    
    def __init__(self, user:User, namespace:Optional[str] = None,id:uuid.UUID = uuid.uuid4()):
        self._user = user
        '''Character of the interface'''
        self._closed:bool = False
        '''Closed'''
        self._id:uuid.UUID = id
        '''ID'''
        self.extra:dict = {}
        '''Extra information'''
        self.commands:Commands = Commands()
        '''Commands of Interface'''

        if namespace != None:
            self.namespace = namespace

        self.logger:log.Logger = log.Logger("interface")
        '''Logger of Interface'''
        formatter = log.Formatter(['%s - %s' % (self.namespace, str(self._id))])
        _handler = log.ConsoleHandler()
        _handler.setFormatter(formatter)
        self.logger.addHandler(_handler)
        if bool(os.environ.get('DEBUG', False)):
            self.logger.setLevel(log.DEBUG)
        else:
            self.logger.setLevel(log.INFO)

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

    @abstractmethod
    async def init(self):
        '''Initial function for Interface'''
        self.logger.debug("Interface %s initializing" % self.id)

    @abstractmethod
    async def final(self):
        '''Finial function for Interface'''
        self.logger.debug("Interface %s finalizing" % self.id)

    @abstractmethod
    async def session_init(self,session:session.Session):
        '''Initial function for Session'''
        pass

    @abstractmethod
    async def session_final(self,session:session.Session):
        '''Finial function for Session'''
        pass

    @abstractmethod
    async def call(self, session:session.Session, message:session.Message):
        '''
        Call the command

        *Note*: Handler Class has add the history, no need to add it again
        Call by this method will skip the command check,
        this command can return any type of value
        '''
        pass
    
    async def close(self):
        '''Close the interface'''
        self._closed = True
        await self.final()

    def register_cmd(self, *args, **kwargs):
        '''Register a command'''
        return self.commands.register(Command(
            in_interface=self,
            *args,
            **kwargs
        ))

from aicompleter.namespace import Namespace
class Interface:
    '''Interface of AI Completer'''
    def __init__(self, user:User, namespace:Optional[str] = None,id:uuid.UUID = uuid.uuid4()):
        self._user = user
        '''Character of the interface'''
        self._closed:bool = False
        '''Closed'''
        self._id:uuid.UUID = id
        '''ID'''
        self.namespace:Namespace = Namespace(
            name=namespace,
            description="Interface %s" % str(self._id),
        )

        self.logger:log.Logger = log.getLogger("interface", ['%s - %s' % (self.namespace.name, str(self._id))])
        '''Logger of Interface'''

    @property
    def data(self):
        '''Data of the interface'''
        return self.namespace.data
    
    @property
    def commands(self):
        '''Commands of the interface'''
        return self.namespace.commands

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

    async def init(self) -> None:
        '''Initial function for Interface'''
        self.logger.debug("Interface %s initializing" % self.id)

    async def final(self) -> None:
        '''Finial function for Interface'''
        self.logger.debug("Interface %s finalizing" % self.id)

    @abstractmethod
    async def session_init(self,session:session.Session) -> None:
        '''Initial function for Session'''
        pass

    @abstractmethod
    async def session_final(self,session:session.Session) -> None:
        '''Finial function for Session'''
        pass

    @abstractmethod
    async def call(self, session:session.Session, message:session.Message):
        '''
        Call the command

        *Note*: Handler Class has add the history, no need to add it again
        Call by this method will skip the command check,
        this command can return any type of value
        '''
        pass
    
    async def close(self):
        '''Close the interface'''
        self._closed = True
        await self.final()

    def register_cmd(self, *args, **kwargs):
        '''Register a command'''
        kwargs.pop("in_interface", None)
        return self.commands.register(Command(
            in_interface=self,
            *args,
            **kwargs
        ))

