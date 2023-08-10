from __future__ import annotations

import logging
import time
import uuid
import attr

from enum import Enum, unique
from typing import Callable, Coroutine

@unique
class Type(Enum):
    '''Event Type'''
    Exception = 1
    '''Exception'''
    Message = 2
    '''Message'''
    KeyboardInterrupt = 3
    '''KeyboardInterrupt'''
    Hook = 4
    '''Hook'''

@attr.s(auto_attribs=True, kw_only=True)
class Event:
    '''Base class for all events'''
    type:Type = attr.ib(default=Type.Exception, validator=attr.validators.instance_of(Type), kw_only=False)
    '''Type of the event'''
    callbacks:list[Callable[[Event,*object],Coroutine[bool, None, None]]] = attr.ib(factory=list, validator=attr.validators.deep_iterable(member_validator=attr.validators.instance_of(Callable), iterable_validator=attr.validators.instance_of(list)))
    '''
    Callback functions
    When a callback function returns True, the event will be stopped
    '''
    data:dict = attr.ib(factory=dict, validator=attr.validators.deep_mapping(key_validator=attr.validators.instance_of(str), value_validator=attr.validators.instance_of(object)))
    '''Extra information'''

    def __attrs_post_init__(self):
        self.last_active_time = time.time()
        '''Last active time'''

    async def __call__(self, *args, **kwargs):
        self.last_active_time = time.time()
        for cb in self.callbacks:
            if (await cb(self, *args, **kwargs)):
                return cb
        return None

    def trigger(self, *args, **kwargs):
        '''
        Trigger the event
        
        When triggered, the callbacks will be called orderly unless one of them returns True

        Returns:
            The callback function that returns True, or None if no callback returns True
        '''
        return self(*args, **kwargs)

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
    
    def __call__(self, e:BaseException, *obj:object):
        return super().__call__(e, *obj)

__all__ = (
    'Type',
    'Event',
    'Exception',
)
