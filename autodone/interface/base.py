'''
Base Objects for Interface of AutoDone-AI
'''
from abc import abstractmethod
import uuid
from enum import Enum, unique
import attr
import autodone.session as session
from command import Command
from autodone import error

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
    def __init__(self, character:Character, id:uuid.UUID = uuid.uuid4()):
        self.character = character
        '''Character of the interface'''
        self._closed:bool = False
        '''Closed'''
        self.id:uuid.UUID = id
        '''ID'''
        self.extra:dict = {}
        '''Extra information'''
        self.commands:set[Command] = set()

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
        pass

    @abstractmethod
    async def final(self):
        '''Finial function for Interface'''
        pass

    @abstractmethod
    async def session_init(self,session:session.Session):
        '''Initial function for Session'''
        pass

    @abstractmethod
    async def session_final(self,session:session.Session):
        '''Finial function for Session'''
        pass

    @abstractmethod
    async def call(self, session:session.Session, command:Command, message:session.Message):
        pass

    def input(self,session:session.Session, message:session.Message):
        '''
        Input function for Session
        The Message contain a `cmd` parameter for function 'call' to use.
        '''
        cmd = self.check_cmd_support(message.cmd)
        if cmd == None:
            raise error.CommandNotFound('Command',self)
        return self.call(session, cmd, message)
    
