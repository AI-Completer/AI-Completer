'''
Base Objects for Interface of AutoDone-AI
'''
from abc import abstractmethod
from typing import Optional
import uuid
from enum import Enum, unique
import attr
from .command import CommandSet, Command
import autodone.session as session
from autodone import error, log
from autodone.config import Config

@unique
class Role(Enum):
    '''Interface Role'''
    USER = 1
    SYSTEM = 2
    AGENT = 3

User = Role.USER
'''User Behind the interface'''
System = Role.SYSTEM
'''System Behind the interface'''
Agent = Role.AGENT
'''AI Agent Behind the interface'''

@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Character:
    '''Interface Character'''
    name:str = ""
    id:uuid.UUID = uuid.uuid4()
    description:str|None = None
    role:Role = System

    support_text:bool = True
    support_image:bool = False
    support_audio:bool = False

class Interface:
    '''Interface of AutoDone-AI'''
    namespace:str = ""
    def __init__(self, character:Character, namespace:Optional[str] = None,id:uuid.UUID = uuid.uuid4()):
        self.character = character
        '''Character of the interface'''
        self._closed:bool = False
        '''Closed'''
        self._id:uuid.UUID = id
        '''ID'''
        self.extra:dict = {}
        '''Extra information'''
        self.commands:CommandSet = CommandSet()
        '''Command Set of Interface'''
        self.config:Config = Config()
        self.config.readonly = True
        '''Config of Interface(Not Writeable)'''

        if namespace != None:
            self.namespace = namespace

        self.logger:log.Logger = log.Logger("interface")
        '''Logger of Interface'''
        formatter = log.Formatter(['%s - %s' % (self.namespace, str(self._id))])
        _handler = log.ConsoleHandler()
        _handler.setFormatter(formatter)
        self.logger.addHandler(_handler)
        if self.config['debug']:
            self.logger.setLevel(log.DEBUG)
        else:
            self.logger.setLevel(log.INFO)

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
        Call by this method will skip the command check
        '''
        pass
    
    async def close(self):
        '''Close the interface'''
        self._closed = True
        self.logger.debug("Interface %s closing" % self.id)
        await self.final()
