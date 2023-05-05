'''
Base Objects for Interface of AutoDone-AI
'''
from abc import abstractmethod
import uuid
from enum import Enum, unique
import attr

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

    @abstractmethod
    async def init(self):
        '''Initial function for Interface'''
        pass

    @abstractmethod
    async def final(self):
        '''Finial function for Interface'''
        pass

    
