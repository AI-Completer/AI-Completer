from __future__ import annotations
from abc import abstractmethod
from ast import Call
from enum import Enum, unique
import time
import logging
from typing import Callable
import uuid
import attr

@unique
class Type(Enum):
    '''Event Type'''
    Exception = 1
    '''Exception'''
    Message = 2
    '''Message'''

@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Event:
    '''Base class for all events'''
    id:uuid.UUID = uuid.uuid4()
    '''ID'''
    type:Type
    '''Type of the event'''
    callback:Callable[[Event,*object],]|None = None
    '''Callback function'''
    extra:dict = {}
    '''Extra information'''

    def __attrs_post_init__(self):
        self.last_active_time = time.time()
        '''Last active time'''
    
    def __call__(self,*args,**kwargs):
        if self.callback is not None:
            self.last_active_time = time.time()
            self.callback(self,*args,**kwargs)

    def trigger(self,*args,**kwargs):
        '''Trigger the event'''
        self.__call__(*args,**kwargs)

class Exception(Event):
    '''Exception Event'''

    callback:Callable[[Event,Exception,*object],]|None = None
    '''Callback function'''

    def __init__(self,exception:Exception) -> None:
        super().__init__()
        self.type = Type.Exception
        '''Type of the event'''
        self.exception = exception
        '''Exception'''

    def reraise(self):
        '''Reraise the exception'''
        raise self.exception
    