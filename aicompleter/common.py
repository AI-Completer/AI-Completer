'''
This is a common module for aicompleter
including some template classes
'''

from abc import ABC, ABCMeta, abstractmethod
from asyncio import iscoroutine
import asyncio
import threading
from typing import Any, Callable, Coroutine, Generic, Optional, Self, TypeVar, overload
import pickle
import contextlib

class SingletonMeta(type):
    '''
    The mata class for singleton
    '''
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        cls._instance = None

    def __call__(cls, *param, **kwparam):
        if cls._instance is None:
            cls._instance = super().__call__(*param, **kwparam)
        return cls._instance
    
class Singleton(metaclass=SingletonMeta):
    '''
    This class is used to create singleton class
    '''
    __slots__ = ()

class JsonTypeMeta(type):
    def __instancecheck__(self, __instance: Any) -> bool:
        if isinstance(__instance, (str, int, float, bool, type(None))):
            return True
        if isinstance(__instance, list):
            return all(isinstance(i, self) for i in __instance)
        if isinstance(__instance, dict):
            return all(isinstance(i, str) and isinstance(j, self) for i, j in __instance.items())
        return False

class JsonType(metaclass=JsonTypeMeta):
    '''
    The type of json
    '''
    __slots__ = ()
    def __new__(cls, *param) -> dict[str, Self] | list[Self] | str | int | float | bool | None:
        if len(param) > 1:
            raise TypeError(f'JsonType accept no more than 1 parameter, got {len(param)}')
        if len(param) == 0:
            return {}
        return param[0]

    def __init_subclass__(cls) -> None:
        raise TypeError(f"Cannot subclass {cls.__name__}")

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
    def __class_getitem__(cls, item: type[_T]) -> Self:
        if not isinstance(item, type):
            raise TypeError("Require type parameter")
        ret = super().__class_getitem__(item)
        if not hasattr(ret, '__sync_classes__'):
            ret.__sync_classes__ = (item,)
        else:
            ret.__sync_classes__ += (item,)
        return ret

class SerializableMeta(ABCMeta):
    '''
    The mata class for serializable
    '''
    def __subclasscheck__(cls: ABCMeta, subclass: type) -> bool:
        if cls == Serializable:
            return hasattr(subclass, '__serialize__') and hasattr(subclass, '__deserialize__')
        return type.__subclasscheck__(cls, subclass)
    
    def __instancecheck__(cls: ABCMeta, instance: Any) -> bool:
        return issubclass(type(instance), cls)

class Serializable(BaseTemplate, metaclass=SerializableMeta):
    '''
    This class is used to serialize object to string

    Warning: Unsecure and unstable for different python version and program version
    '''
    __slots__ = ()
    def __serialize__(self) -> bytes:
        '''
        Convert to string format
        '''
        return pickle.dumps(self)
    
    @staticmethod
    def __deserialize__(src: bytes) -> Self:
        '''
        Get a object from a string

        This method will not verify the type of the object, you may not get a object of the same type
        '''
        return pickle.loads(src)

class JSONSerializable(Serializable):
    '''
    This class is used to serialize object to json
    '''
    def __serialize__(self) -> list:
        '''
        Convert to json format
        '''
        return {
            key: serialize(value) for key, value in self.__dict__.items()
        }

    @classmethod
    def __deserialize__(cls, data:dict) -> Self:
        '''
        Get a object from a json, this method will be implemented by metaclass
        '''
        ret = cls.__new__(cls)
        ret.__dict__ = {
            key: deserialize(value) for key, value in data.items()
        }
        return ret

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

    @classmethod
    @abstractmethod
    def load(cls, path: str, *args, **kwargs) -> Self:
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

    @classmethod
    @abstractmethod
    async def load(cls, path: str) -> Self:
        '''
        Load from file
        '''
        raise NotImplementedError('load is not implemented')

class ContentManager(BaseTemplate):
    '''
    This class is a template for content manager
    '''
    __slots__ = ()
    def __enter__(self):
        '''
        Enter the context
        '''
        if hasattr(self, 'acquire') and callable(self.acquire):
            self.acquire()
        raise NotImplementedError('enter is not implemented')
    
    def __exit__(self, exc_type, exc_value, traceback):
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
    __slots__ = ()
    async def __aenter__(self):
        '''
        Enter the context
        '''
        if hasattr(self, 'acquire') and callable(self.acquire):
            await self.acquire()
        raise NotImplementedError('enter is not implemented')
    
    async def __aexit__(self, exc_type, exc_value, traceback):
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

    @property
    def closed(self) -> bool:
        '''
        Whether the object is closed
        '''
        return self._close_event.is_set()
    
    async def close(self) -> None:
        '''
        Close the object
        '''
        self._close_event.set()

    async def wait_close(self) -> Coroutine[None, None, None]:
        '''
        Wait until the object is closed
        '''
        await self._close_event.wait()

    def __del__(self) -> None:
        # Sometimes, this will be called randomly? (I don't know why)
        if '_close_event' not in self.__dict__:
            return
        if not self.closed:
            print(f"Warning: The object is not closed: {self!r}")

class SerializeHandler(Generic[_T]):
    '''
    The class for serialize handler

    :param _T: The type of the object
    '''
    _serialize_handlers: dict[type, Self] = {}

    def __new__(cls, param: type[_T]) -> Self:
        if not isinstance(param, type):
            raise TypeError("Require type parameter")
        if param in cls._serialize_handlers:
            return cls._serialize_handlers[param]
        else:
            ret = super().__new__(cls)
            cls._serialize_handlers[param] = ret
            return ret

    def serializer(self, func: Callable[[_T], JsonType]):
        '''
        Register the serialize handler
        '''
        self.__serializer = func

    def deserializer(self, func: Callable[[JsonType], _T]):
        '''
        Register the deserializer handler
        '''
        self.__deserializer = func

    def serialize(self, data:_T) -> JsonType:
        ret = self.__serializer(data)
        if not isinstance(ret, JsonType):
            raise TypeError("The return value of serializer must be JsonType")
        return ret
    
    def deserialize(self, data:JsonType) -> _T:
        if not isinstance(data, JsonType):
            raise TypeError("The data must be JsonType")
        return self.__deserializer(data)
    
    @staticmethod
    @overload
    def support(type_:type):...
    
    @staticmethod
    @overload
    def support(data: Any):...

    @staticmethod
    def support(param: Any):
        if isinstance(param, type):
            return issubclass(param, tuple(SerializeHandler._serialize_handlers.keys()))
        else:
            return isinstance(param, tuple(SerializeHandler._serialize_handlers.keys()))
        
    @staticmethod
    def serializeData(data: Any):
        if not SerializeHandler.support(data):
            raise TypeError("The data type is not support")
        # Get the type
        for type_ in SerializeHandler._serialize_handlers:
            if isinstance(data, type_):
                return type_, SerializeHandler(type_).serialize(data)
        raise Exception("Unknown Error")

def _get_class(module:str, class_:str):
    import importlib
    module_ = importlib.import_module(module)
    # Split the submodule
    for i in class_.split('.'):
        module_ = getattr(module_, i)
    return module_

def serialize(data:Any, pickle_all:bool = False) -> JsonType:
    '''
    Convert to serial format (in json)

    :param data: The data to be serialized
    :param pickle_all: Whether to pickle all the data, this is dangerous because it will execute the code in the data
    '''
    if isinstance(data, Serializable):
        return {
            'type': 'class',
            'module': data.__module__,
            'class': data.__class__.__qualname__,
            'data': data.__serialize__(),
        }
    elif isinstance(data, (list, set, tuple)):
        subtype = data.__class__.__qualname__
        if subtype not in ('list', 'set', 'tuple'):
            return {
                'type': 'yield-subclass',
                'module': data.__class__.__module__,
                'class': data.__class__.__qualname__,
                'data': [serialize(item) for item in data],
            }
        return {
            'type': subtype,
            'data': [serialize(item) for item in data],
        }
    elif isinstance(data, dict):
        if type(data) is not dict:
            return {
                'type': 'dict-subclass',
                'module': data.__class__.__module__,
                'class': data.__class__.__qualname__,
                'data': {
                    key: serialize(value) for key, value in data.items()
                },
            }
        return {
            'type': 'dict',
            'data': {
                key: serialize(value) for key, value in data.items()
            },
        }
    elif isinstance(data, (int, float, str, bool, type(None))):
        subtype = data.__class__.__qualname__
        if subtype not in ('int', 'float', 'str', 'bool', 'NoneType'):
            if pickle_all:
                return {
                    'type': 'pickle',
                    'data': pickle.dumps(data),
                }
            raise TypeError(f'Cannot serialize {data}({type(data)}), this class is inherited from {subtype}')
        return data
    elif isinstance(data, bytes):
        return {
            'type': 'bytes',
            'data': data.hex(),
        }
    elif isinstance(data, type):
        # Get the module and class name
        return {
            'type': 'type',
            'module': data.__module__,
            'class': data.__qualname__,
        }
    elif SerializeHandler.support(data):
        # Search the match type
        cls, ddata = SerializeHandler.serializeData(data)
        return {
            'type': 'handler',
            'module': cls.__module__,
            'class': cls.__qualname__,
            'data': ddata,
        }
    elif hasattr(data, '__setstate__') and hasattr(data, '__getstate__'):
        # Allow secure pickle
        return {
            'type': 'secure-pickle',
            'data': pickle.dumps(data).hex(),
        }
    else:
        if pickle_all:
            return {
                'type': 'pickle',
                'data': pickle.dumps(data),
            }
        raise TypeError(f'Cannot serialize {data}({type(data)})')

def deserialize(data: JsonType, global_:Optional[dict[str, Any]] = None, unpickle_all:bool = False) -> Any:
    '''
    Get a object from serial format (in json)

    :param data: The data to be deserialized
    :param global_: The global variables, if none, will try import the module(warning: this is dangerous)
    :param unpickle_all: Whether to unpickle all the data, this is dangerous because it will execute the code in the data
    '''
    if isinstance(data, (int, float, str, bool, type(None))):
        return data
    if 'type' not in data:
        raise TypeError(f'Cannot deserialize {data}({type(data)})')
    subtype = data['type']
    if subtype == 'class':
        if global_ is None:
            cls = _get_class(data['module'], data['class'])
        else:
            cls = global_
            for i in data['class'].split('.'):
                cls = cls[i]
        if not issubclass(cls, Serializable):
            raise TypeError(f'Cannot deserialize {data}({type(data)}), this class is not inherited from Serializable')
        return cls.__deserialize__(data['data'])
    elif subtype in ('list', 'set', 'tuple'):
        import builtins
        return getattr(builtins, subtype)([deserialize(item) for item in data['data']])
    elif subtype == 'yield-subclass':
        cls = _get_class(data['module'], data['class'])
        if not issubclass(cls, (list, set, tuple)):
            raise TypeError(f'Cannot deserialize {data}({subtype}), this class is not inherited from {subtype}')
        return cls([deserialize(item) for item in data['data']])
    elif subtype == 'dict':
        return {key: deserialize(value) for key, value in data['data'].items()}
    elif subtype == 'dict-subclass':
        cls = _get_class(data['module'], data['class'])
        if not issubclass(cls, dict):
            raise TypeError(f'Cannot deserialize {data}({subtype}), this class is not inherited from dict')
        ret = cls()
        ret.update({key: deserialize(value) for key, value in data['data'].items()})
        return ret
    elif subtype == 'bytes':
        # hex转bytes
        return bytes.fromhex(data['data'])
    elif subtype == 'type':
        cls = _get_class(data['module'], data['class'])
        return cls
    elif subtype == 'handler':
        cls = _get_class(data['module'], data['class'])
        if not SerializeHandler.support(cls):
            raise ValueError("Serializer type not support")
        return SerializeHandler(cls).deserialize(data['data'])
    elif subtype == 'secure-pickle':
        # Consider to remove this feature
        # Because it's difficult to verify the security of the pickle
        return pickle.loads(bytes.fromhex(data['data']))
    elif subtype == 'pickle':
        if unpickle_all:
            return pickle.loads(data['data'])
        raise TypeError(f'Cannot deserialize {data}({subtype}), this class is a pickle object')
    else:
        raise TypeError(f'Cannot deserialize {data}({subtype}), unknown type')

# add default handler
import uuid
@SerializeHandler(uuid.UUID).serializer
def _(data:uuid.UUID) -> str:
    return data.hex

@SerializeHandler(uuid.UUID).deserializer
def _(data:str) -> uuid.UUID:
    return uuid.UUID(data)

@SerializeHandler(asyncio.Lock).serializer
def _(data: asyncio.Lock) -> bool:
    return data.locked()

@SerializeHandler(asyncio.Lock).deserializer
def _(data: bool) -> asyncio.Lock:
    lock = asyncio.Lock()
    if data:
        asyncio.run(lock.acquire())
    return lock

__all__ = (
    'BaseTemplate',
    *(
        i.__name__ for i in globals().values() if isinstance(i, type) and issubclass(i, BaseTemplate)
    ),

    'serialize',
    'deserialize',
    'SerializeHandler',
    'JsonType',
)
