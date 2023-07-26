'''
This is a common module for aicompleter
including some template classes
'''

from abc import ABC, abstractmethod
from asyncio import iscoroutine
import asyncio
import threading
from typing import Any, Generic, Self, TypeVar
import pickle

class BaseTemplate(ABC):
    '''
    A template class for all the template classes in aicompleter
    '''

_T = TypeVar('_T')
class AsyncTemplate(BaseTemplate, Generic[_T]):
    '''
    A template class for all the asynchronous template classes in aicompleter
    :param _T: The type of the synchronous object(if exists)
    '''
    
    # Hook the subclass and add attr __sync_class__
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        args = [i for i in cls.__orig_bases__ if i.__origin__ == AsyncTemplate][0].__args__
        if len(args) > 0:
            cls.__sync_class__ = args[0]
        else:
            cls.__sync_class__ = None

del _T

class Serializable(BaseTemplate):
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
    def serialize(self) -> dict:
        def _handle(data:Any):
            if isinstance(data, JSONSerializable):
                return data.serialize()
            elif isinstance(data, (list, set, tuple)):
                return [_handle(item) for item in data]
            elif isinstance(data, dict):
                return {key: _handle(value) for key, value in data.items()}
            elif isinstance(data, self.ATTR_ENABLE_TYPES):
                return data
        return {key: _handle(value) for key, value in self.__dict__.items()}

    @staticmethod
    @abstractmethod
    def deserialize(src: dict) -> Self:
        raise NotImplementedError('from_json is not implemented')

class Saveable(BaseTemplate):
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

class AsyncSaveable(AsyncTemplate[Saveable]):
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

class ContentManager(BaseTemplate):
    '''
    This class is a template for content manager
    '''
    def __enter__(self) -> Any:
        '''
        Enter the context
        '''
        if hasattr(self, 'acquire') and callable(self.acquire):
            self.acquire()
        raise NotImplementedError('enter is not implemented')
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        '''
        Exit the context
        '''
        if hasattr(self, 'release') and callable(self.release):
            self.release()
        raise NotImplementedError('exit is not implemented')
    
class AsyncContentManager(AsyncTemplate[ContentManager]):
    '''
    This class is a template for asynchronous content manager
    '''
    async def __aenter__(self) -> Any:
        '''
        Enter the context
        '''
        if hasattr(self, 'acquire') and callable(self.acquire):
            await self.acquire()
        raise NotImplementedError('enter is not implemented')
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        '''
        Exit the context
        '''
        if hasattr(self, 'release') and callable(self.release):
            ret = self.release()
            if iscoroutine(ret):
                return await ret
        raise NotImplementedError('exit is not implemented')

class LifeTimeManager(BaseTemplate):
    '''
    This class is a template for lifetime manager
    '''
    def __init__(self) -> None:
        super().__init__()
        self._close_event:threading.Event = threading.Event()

    @property
    def closed(self) -> bool:
        '''
        Whether the object is closed
        '''
        return self._close_event.is_set()
    
    def close(self) -> None:
        '''
        Close the object
        '''
        self._close_event.set()

    def wait_close(self) -> None:
        '''
        Wait until the object is closed
        '''
        self._close_event.wait()

class AsyncLifeTimeManager(AsyncTemplate[LifeTimeManager]):
    '''
    This class is a template for asynchronous lifetime manager
    '''
    def __init__(self) -> None:
        super().__init__()
        self._close_event:asyncio.Event = asyncio.Event()
        '''
        The close event
        '''
        self._close_tasks:set[asyncio.Future] = set()
        '''
        The tasks that will be waited when the object is closed
        '''

    @property
    def closed(self) -> bool:
        '''
        Whether the object is closed
        '''
        return self._close_event.is_set()
    
    def close(self) -> None:
        '''
        Close the object
        '''
        for task in self._close_tasks:
            if not task.done():
                task.cancel()
        self._close_event.set()

    async def wait_close(self) -> None:
        '''
        Wait until the object is closed
        '''
        await self._close_event.wait()
        for task in self._close_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self._close_tasks)

__all__ = (
    'BaseTemplate',
    *(
        i.__name__ for i in globals().values() if isinstance(i, type) and issubclass(i, BaseTemplate)
    )
)
