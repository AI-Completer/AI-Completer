from __future__ import annotations
from abc import abstractmethod
from ast import Call
from enum import Enum, unique
import time
import logging
from typing import Callable, Coroutine
import uuid
import attr

@unique
class Type(Enum):
    '''Event Type'''
    Exception = 1
    '''Exception'''
    Message = 2
    '''Message'''
    KeyboardInterrupt = 3
    '''KeyboardInterrupt'''

@attr.s(auto_attribs=True, kw_only=True)
class Event:
    '''Base class for all events'''
    id:uuid.UUID = uuid.uuid4()
    '''ID'''
    type:Type = Type.Exception
    '''Type of the event'''
    callbacks:list[Callable[[Event,*object],Coroutine[bool, None, None]]] = []
    '''
    Callback functions
    When a callback function returns True, the event will be stopped
    '''
    extra:dict = {}
    '''Extra information'''

    def __attrs_post_init__(self):
        self.last_active_time = time.time()
        '''Last active time'''

    async def __call__(self, *args, **kwargs):
        self.last_active_time = time.time()
        for cb in self.callbacks:
            if (await cb(self, *args, **kwargs)):
                break

    async def trigger(self, *args, **kwargs):
        '''Trigger the event'''
        await self(*args, **kwargs)

    def add_callback(self, cb:Callable[[Event,*object],Coroutine[bool, None, None]]) -> None:
        '''Add callback function'''
        self.callbacks.append(cb)

class Exception(Event):
    '''Exception Event'''

    callback:Callable[[Event,Exception,*object],]|None = None
    '''Callback function'''

    def __init__(self,exception:Exception) -> None:
        super().__init__(type=Type.Exception)
        self.type = Type.Exception
        '''Type of the event'''
        self.exception = exception
        '''Exception'''

    def reraise(self):
        '''Reraise the exception'''
        raise self.exception
