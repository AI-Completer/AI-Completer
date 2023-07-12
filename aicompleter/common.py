'''
This is a common module for aicompleter
including some template classes
'''

from abc import ABC, abstractmethod
from typing import Any, Self

import pickle

class Serializable(ABC):
    '''
    This class is used to serialize object to string

    Warning: Unsecure and unstable for different python version and program version
    '''
    def serialize(self) -> bytes:
        '''
        Convert to string format
        '''
        return pickle.dumps(self)
    
    @staticmethod
    def deserialize(src: bytes) -> Self:
        '''
        Get a object from a string
        '''
        return pickle.loads(src)

class JSONSerializable(Serializable):
    '''
    This class is used to serialize object to json
    '''
    @abstractmethod
    def serialize(self) -> dict:
        '''
        Convert to json format
        '''
        raise NotImplementedError('to_json is not implemented')

    @staticmethod
    @abstractmethod
    def deserialize(src: dict) -> Self:
        '''
        Get a object from a dict
        '''
        raise NotImplementedError('from_json is not implemented')

class AttrJSONSerializable(JSONSerializable):
    '''
    This class is used to serialize attribute class to json
    '''
    ATTR_ENABLE_TYPES = (
        int, float, str, bool, list, set, dict, tuple, type(None), bytes
    )
    def to_json(self) -> dict:
        def _handle(data:Any):
            if isinstance(data, JSONSerializable):
                return data.to_json()
            elif isinstance(data, (list, set, tuple)):
                return [_handle(item) for item in data]
            elif isinstance(data, dict):
                return {key: _handle(value) for key, value in data.items()}
            elif isinstance(data, self.ATTR_ENABLE_TYPES):
                return data
        return {key: _handle(value) for key, value in self.__dict__.items()}

    @staticmethod
    def from_json(src: dict) -> Self:
        raise NotImplementedError('from_json is not implemented')

class Saveable(ABC):
    '''
    This class is can save object to file
    '''
    @abstractmethod
    def save(self, path: str) -> None:
        '''
        Save to file
        '''
        raise NotImplementedError('save is not implemented')

    @staticmethod
    @abstractmethod
    def load(path: str) -> Self:
        '''
        Load from file
        '''
        raise NotImplementedError('load is not implemented')

class AsyncSaveable(ABC):
    '''
    This class is can save object to file asynchronously
    '''
    @abstractmethod
    async def save(self, path: str) -> None:
        '''
        Save to file
        '''
        raise NotImplementedError('save is not implemented')

    @staticmethod
    @abstractmethod
    async def load(path: str) -> Self:
        '''
        Load from file
        '''
        raise NotImplementedError('load is not implemented')
