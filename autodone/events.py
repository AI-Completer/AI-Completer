from __future__ import annotations
from abc import abstractmethod
import time
import logging
from typing import Callable
import uuid
import attr

@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Event:
    '''Base class for all events'''
    last_active_time:float = time.time()
    '''Last active time'''
    id:uuid.UUID = uuid.uuid4()
    '''ID'''
    callback:Callable[[Event],]|None = None
    '''Callback function'''
    extra:dict = {}
    '''Extra information'''

    def __attrs_post_init__(self):
        self.last_active_time = time.time()
    
    def __call__(self):
        if self.callback is not None:
            self.callback(self)

    def trigger(self):
        '''Trigger the event'''
        self.__call__()

