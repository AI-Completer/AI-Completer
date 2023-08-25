from __future__ import annotations

import asyncio
import functools
import inspect
from types import FrameType
import typing
from typing import (Any, Callable, Coroutine, Iterable, Literal, LiteralString, Mapping, Optional, Self, TypeAlias,
                    TypeVar, overload)

from .. import common
from .typeval import verify

def typecheck(value:Any, type_:type|tuple[type, ...]):
    '''
    Check the type of value. If not, raise TypeError
    '''
    if not isinstance(value, type_):
        raise TypeError(f'Expect {type_}, got {type(value)}')

StructType = TypeVar('StructType', dict, list, type, Callable, tuple)
'''
Struct Type
'''
class Struct:
    '''
    Struct To Check Json Data

    Usage:
    Struct({
        'key1':type,
        'key2':[type],
        'key3':{
            'key4':type,
        }
        'key5':lambda x: x > 0,
        'key6':[{'key7':type}],
        'key8':(type, type),
    })
    '''
    def _check_struct(self, struct:StructType) -> None:
        '''
        Check struct
        '''
        if isinstance(struct, dict):
            for key in struct:
                if not isinstance(key, str):
                    raise TypeError('key must be str')
                if isinstance(struct[key], (list, dict)):
                    self._check_struct(struct[key])
                elif isinstance(struct[key], type):
                    pass
                elif callable(struct[key]):
                    pass
                else:
                    raise TypeError('value must be type or callable')
            return
        if isinstance(struct, list):
            if len(struct) != 1:
                raise TypeError('list must have only one element')
            for item in struct:
                self._check_struct(item)
            return
        if isinstance(struct, type):
            return
        if callable(struct):
            return
        if isinstance(struct, tuple):
            # Check every item in tuple
            for item in struct:
                self._check_struct(item)
            return
        raise TypeError('struct must be dict or list or type or callable or tuple')
    
    def __init__(self ,struct:StructType) -> None:
        self.struct = struct
        self._check_struct(struct)

    def check(self, data:Any, allow_extra:bool = True) -> bool:
        '''
        Check data(No allow extra keys)
        '''
        def _check(struct:StructType, data:Any) -> bool:
            if isinstance(struct, dict):
                if not isinstance(data, dict):
                    return False
                for key in struct:
                    if key not in data:
                        return False
                    if not _check(struct[key], data[key]):
                        return False
                if not allow_extra and set(struct.keys()) < set(data.keys()):
                    # Extra keys
                    return False
                return True
            if isinstance(struct, list):
                if not isinstance(data, list):
                    return False
                for item in data:
                    if not _check(struct[0], item):
                        return False
                return True
            if isinstance(struct, type):
                return isinstance(data, struct) if struct != Any else True
            if callable(struct):
                return struct(data)
            if isinstance(struct, tuple):
                # Check every item in tuple
                for item in struct:
                    if not _check(item, data):
                        return False
                return True
            raise TypeError('struct must be dict or list or type or callable')
        
        return _check(self.struct, data)
    
class overload_func:
    '''
    Overload decorator
    '''
    def __new__(cls) -> Self:
        raise NotImplementedError('Overload is not fully implemented yet')

    def __init__(self, func:Callable) -> None:
        self.func = func
        '''Function to overload'''
        self.__doc__ = func.__doc__
        self.__name__ = func.__name__
        self.__qualname__ = func.__qualname__
        self.__annotations__ = func.__annotations__

        self.regs:list[Callable] = []
        '''Overload register'''
        typing.overload(func)
        # Add Overload Register

    def register(self, func:Callable) -> None:
        '''
        Register a function
        '''
        self.regs.append(func)
        return self

    def __call__(self, *args:Any, **kwargs:Any) -> Callable:
        '''
        Call the function
        '''
        def _check_instance(value:Any, type_name:str) -> bool:
            if hasattr(value, '__bases__'):
                for base in value.__bases__:
                    if base.__name__ == type_name:
                        return True
                    if _check_instance(base, type_name):
                        return True
            return value.__class__.__name__ == type_name
        
        check_match = lambda value: info.parameters[name].annotation not in (Any, inspect._empty) and not _check_instance(value, info.parameters[name].annotation)
        
        for func in self.regs:
            info = inspect.signature(func)
            # Match func and args,kwargs with annotation
            is_match:bool = True
            typing.get_type_hints(func)
            for i, arg in enumerate(args):
                name = tuple(info.parameters.keys())[i]
                if check_match(name):
                    is_match = False
                    break
            if not is_match:
                continue
            for key, value in kwargs.items():
                if check_match(value):
                    is_match = False
                    break
            if not is_match:
                continue
            return func(*args, **kwargs)
        return self.func(*args, **kwargs)

_T = TypeVar('_T')
def hookclass(obj:_T, hooked_vars:dict[str, Any])-> _T:
    '''
    Hook class varible

    After wrapped by this function
    You will have a copy of the hooked_vars when using the class,

    Note:
    -----
    When passing list, dict, or so on of cantainer type in hooked_vars, you should use a copy

    Examples:
    ---------
    ::
        >>> class A:
        ...     def __init__(self):
        ...         self.a = 1
        ...         self.b = 2
        ...     def func(self):
        ...         return self.a + self.b
        >>> a = A()
        >>> a.func()
        3
        >>> b = hookclass(a, {'a': 2})
        >>> b.func()
        4
        >>> a.a
        1
        >>> b.a
        2
        >>> b.a = 3
        >>> b.func()
        5
        >>> a.func()
        3
        >>> b.b = 4
        >>> a.b
        4
    '''
    class Deleted:
        ...
    class _HookClass:
        def __init__(self):
            self.__old_vars = {}

        def __enter__(self):
            for k, v in hooked_vars.items():
                self.__old_vars[k] = getattr(obj, k)
                if v is Deleted:
                    delattr(obj, k)
                else:
                    setattr(obj, k, v)
            return obj
        
        def __exit__(self, exc_type, exc_value, traceback):
            for k, v in self.__old_vars.items():
                hooked_vars[k] = getattr(obj, k, Deleted)
                setattr(obj, k, v)
    hooker_env = _HookClass()
    
    class HookMeta(type):
        def __new__(cls, name, bases, namespace):
            def _wrap(name):
                @functools.wraps(getattr(obj, name))
                def _wrapped(*args, **kwargs):
                    with hooker_env as obj:
                        if len(args) >= 1 and isinstance(args[0], HookClass):
                            args = args[1:]
                        return getattr(obj, name)(*args, **kwargs)
                return _wrapped
            for k, v in type(obj).__dict__.items():
                if k in ('__setattr__', '__getattribute__', '__delattr__', '__init__', '__new__'):
                    continue
                if callable(v):
                    namespace[k] = _wrap(k)
            namespace['__wrapped__'] = obj
            
            ret = super().__new__(cls, name, bases, namespace)
            return ret
        
    class HookClass(metaclass=HookMeta):

        @functools.wraps(obj.__setattr__)
        def __setattr__(self, __name: str, __value: Any) -> None:
            if __name.startswith("__") or __name.startswith("_HookClass__"):
                return super().__setattr__(__name, __value)
            with hooker_env as obj:
                return setattr(obj, __name, __value)
            
        @functools.wraps(obj.__getattribute__)
        def __getattribute__(self, __name: str) -> Any:
            with hooker_env as obj:
                ret = getattr(obj, __name)
                if hasattr(ret, '__call__'):
                    @functools.wraps(ret)
                    def _wrapped(*args, **kwargs):
                        with hooker_env as obj:
                            return getattr(obj, __name)(*args, **kwargs)
                    return _wrapped
                return ret
        
        @functools.wraps(obj.__delattr__)
        def __delattr__(self, __name: str) -> None:
            if __name.startswith("__") or __name.startswith("_HookClass__"):
                return super().__delattr__(__name)
            with hooker_env as obj:
                return delattr(obj, __name)

    return HookClass()

del _T

@overload
def link_property(link:str, *, enable_set=True, enable_del=True, doc=None):...

@overload
def link_property(linkdict:dict, key:str, *, enable_set=True, enable_del=True, doc=None):...

@overload
def link_property(linkdict:str, key:str, *, enable_set=True, enable_del=True, doc=None):...

def link_property(link: str|dict, key:Optional[str]=None, *, enable_set=True, enable_del=True, doc=None):
    '''
    Link a property to the link

    Examples
    ---------
    ::
        >>> dic = {'k': "value"}
        >>> class A:
        ...     def __init__(self):
        ...         self.b = 1
        ...         self.c = {'key':'value'}
        ...     a = link_property('b')
        ...     d = link_property('c', 'key')
        ...     k = link_property(dic, 'k')
        >>> a = A()
        >>> a.a
        1
        >>> a.a = 2
        >>> a.b
        2
        >>> a.d
        'value'
    '''
    if isinstance(link,str) and key == None:
        # link is a class name
        def _get(self):
            return getattr(self, link)
        def _set(self, value):
            return setattr(self, link)
        def _del(self):
            return delattr(self, link)
    
    if isinstance(link, dict):
        if key == None:
            raise TypeError('key must be str')
        # link is a dict
        def _get(self):
            return link[key]
        def _set(self, value):
            link[key] = value
        def _del(self):
            del link[key]
    
    if isinstance(link, str) and isinstance(key, str):
        # link is a dict
        def _get(self):
            return getattr(self, link)[key]
        def _set(self, value):
            getattr(self, link)[key] = value
        def _del(self):
            del getattr(self, link)[key]
        ret = property(_get)
        
    if '_get' not in locals():
        raise TypeError('link must be str or dict')

    _get.__doc__ = doc
    ret = property(_get)
    if enable_set:
        ret = ret.setter(_set)
    if enable_del:
        ret = ret.deleter(_del)
    return ret

def appliable_parameters(func:Callable, parameters:dict[str, Any]) -> dict[str, Any]:
    '''
    Get the appliable parameters of func
    '''
    ret = {}
    from .typeval import get_signature
    sig = get_signature(func)
    for name, value in parameters.items():
        if name in sig.parameters:
            ret[name] = value
    return ret

class BaseModel:
    '''
    Base defination of Model
    '''
def make_model(model_base:type, 
               doc:Optional[str] = None):
    '''
    This function will make a dict-like class be a model class

    If the handlers are set, this can also make other class be a model class
    '''
    assert isinstance(model_base, type), 'model_base must be a type'

    class ModelProperty:
        '''
        Configuration Model Property
        '''
        @staticmethod
        def default_getter(instance:Model, owner:type, property: ModelProperty) -> Any:
            ret = instance.__wrapped__[property.key]
            if isinstance(ret, model_base) and property.model_factory:
                return property.model_factory(ret)
            return ret
        
        @staticmethod
        def default_setter(instance:Model, property: ModelProperty, value:Any) -> None:
            instance.__wrapped__[property.key] = value

        @staticmethod
        def default_deleter(instance:Model, property: ModelProperty) -> None:
            del instance.__wrapped__[property.key]

        def __init__(self, 
                     key:str, 
                     model_factory:Optional[type[Model]]=None,
                     getter:Optional[Callable[[Model, type, ModelProperty], Any]] = None,
                     setter:Optional[Callable[[Model, ModelProperty, Any], None]] = None,
                     deleter:Optional[Callable[[Model, ModelProperty], None]] = None):
            self.key = key
            self.model_factory = model_factory
            self.getter = getter or self.default_getter
            self.setter = setter or self.default_setter
            self.deleter = deleter or self.default_deleter
        
        def __get__(self, instance:Model, owner:type) -> Any:
            return self.getter(instance, owner, self)
            
        def __set__(self, instance:Model, value:Any) -> None:
            return self.setter(instance, self, value)

        def __delete__(self, instance:Model) -> None:
            return self.deleter(instance, self)

    # This operation is to solve the metaclass conflict
    base_metaclass = type(model_base)

    class ModelMeta(base_metaclass):
        Factory:TypeAlias = model_base
        def __new__(cls, name:str, bases:tuple[type,...], attrs:dict, / ,
                    init:bool = False, global_:Optional[dict[str, Any]] = None, local_:Optional[Mapping[str, Any]] = None):
            '''
            Create a model class

            Parameters
            -----------
            init: bool, Optional, default: True, whether to generate __init__ by annotations
            global_: dict[str, Any], Optional, default: None, global variables, if None, will try to obtain stack frame and get global variables
            local_: Mapping[str, Any], Optional, default: None, local variables, if None, will use attrs
            '''
            import inspect
            if '__annotations__' not in attrs:
                return super().__new__(cls, name, bases, attrs)
            annotations:dict = attrs['__annotations__']
            defaults = {}

            global_ = global_ or inspect.stack()[1][0].f_globals
            local_ = local_ or attrs

            for k, v in annotations.items():
                if k in attrs:
                    defaults[k] = attrs[k]
                # Ensure when the subclass is get, it will return a ConfigModel
                # Try to eval the type annotation
                if isinstance(v, str):
                    v = eval(v, global_, local_)
                attrs[k] = ModelProperty(k, v if isinstance(v, type) and issubclass(v, model_base) else None)
            attrs['__defaults__'] = defaults
            attrs['__models__'] = annotations
            attrs['__model_attrs__'] = attrs
            attrs['__wrapped__'] = None
            # Hook config method
            # bases = (base for base in bases if base is not cls.ConfigFactory)
            for name, method in inspect.getmembers(cls.Factory):
                if not callable(method):
                    continue
                if name in ('__new__', '__getattribute__', '__setattr__', '__delattr__', '__eq__', '__ne__', '__class__'):
                    continue
                def _wrap(name, method):
                    def _replace(self:Model, *args, **kwargs):
                        return getattr(self.__wrapped__, name)(*args, **kwargs)
                    return _replace
                if name not in attrs:
                    attrs[name] = _wrap(name, method)
            
            if init:
                # Generate __init__
                def __init__(self, *args, **kwargs) -> None:
                    # There is a rewrite problem
                    # When use Model(**kwargs), the model_base will be created and this funcion is no need to run
                    import inspect
                    params = []
                    for k, v in annotations.items():
                        if k == 'return':
                            continue
                        params.append(inspect.Parameter(k, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=v, default=defaults.get(k, inspect._empty)))
                    sig = inspect.Signature(params, return_annotation=None)
                    bind = sig.bind(*args, **kwargs)
                    bind.apply_defaults()
                    for k, v in bind.arguments.items():
                        setattr(self, k, v)
                # wrap __init__
                __init__.__annotations__ = annotations
                __init__.__annotations__['return'] = None
                __init__.__qualname__ = f'{name}.__init__'
                __init__.__name__ = '__init__'
                attrs['__init__'] = __init__
            
            if doc != None:
                attrs['__doc__'] = doc
            ret = super().__new__(cls, name, bases, attrs)
            return ret
        
    class Model(model_base, BaseModel, metaclass=ModelMeta):
        def __new__(cls, *args, **kwargs) -> Self:
            self = super().__new__(cls)
            if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], model_base):
                config = args[0]
            else:
                config = model_base(*args, **kwargs)
            self.__wrapped__ = config
            for k,v in self.__defaults__.items():
                if k not in config:
                    setattr(self, k, v)
                # use setattr to avoid __setattr__ hook
            return self
        
        def __init__(self, *args, **kwargs) -> None:
            # Do nothing, avoid __init__ autocall
            pass
        
        def __getattribute__(self, name:str) -> Any:
            if name in ('__wrapped__', '__defaults__', '__models__', '__model_attrs__'):
                return super().__getattribute__(name)
            if name in self.__models__:
                return super().__getattribute__(name)
            if name in self.__model_attrs__:
                return super().__getattribute__(name)
            return getattr(self.__wrapped__, name)
        
        def __setattr__(self, name:str, value:Any) -> None:
            if name == '__wrapped__':
                super().__setattr__(name, value)
                return
            if name in self.__models__:
                super().__setattr__(name, value)
                return
            if name in self.__model_attrs__:
                super().__setattr__(name, value)
                return
            setattr(self.__wrapped__, name, value)

        def __delattr__(self, __name: str) -> None:
            if __name == '__wrapped__':
                raise TypeError("can't delete __wrapped__")
            if __name in self.__models__:
                super().__delattr__(__name)
                return
            if __name in self.__model_attrs__:
                super().__delattr__(__name)
                return
            delattr(self.__wrapped__, __name)

        def __eq__(self, right: Self) -> bool:
            if not isinstance(right, type(self)):
                return False
            return self.__wrapped__ == right.__wrapped__
        
        def __ne__(self, right: Self) -> bool:
            if not isinstance(right, type(self)):
                return True
            return self.__wrapped__ != right.__wrapped__
    
    return Model

def asdict(model: BaseModel, filter:Optional[Callable[[str, Any], bool]]=None) -> dict[str, Any]:
    '''
    Convert model to dict

    Parameters
    ----------
    model: BaseModel, the model to convert
    filter: Callable[[str, Any], bool], Optional, default: None, the filter function, if return True, the key-value will be added to the dict
    '''
    ret = {}
    for k, v in model.__models__.items():
        if filter and not filter(k, getattr(model, k)):
            continue
        ret[k] = getattr(model, k)
    return ret

class TaskList(common.AsyncContentManager, list[asyncio.Task]):
    '''
    Asyncio Task list
    '''
    @overload
    def __init__(self) -> None:...
    @overload
    def __init__(self, _iterable:Iterable[asyncio.Task]) -> None:...

    def __init__(self, _iterable:Optional[Iterable[asyncio.Task]]=None) -> None:
        super().__init__()
        if _iterable:
            self.extend(_iterable)
    
    class TaskSession:
        '''
        Task Session
        '''
        def __init__(self, task: asyncio.Task) -> None:
            self.task = task
            self._in_list: Optional[TaskList] = None

        @classmethod
        def _setup_list(cls, task: asyncio.Task, task_list: TaskList) -> Self:
            ret = cls(task)
            ret._in_list = task_list
            return ret

        async def __aenter__(self) -> asyncio.Task:
            if self._in_list:
                self._in_list.append(self.task)
            return self.task
        
        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            if not self.task.done():
                await self.task
            if self._in_list:
                self._in_list.remove(self.task)

    def session(self, task: asyncio.Task | Coroutine[None, None, Any], loop:Optional[asyncio.AbstractEventLoop] = None) -> TaskSession:
        '''
        Get a session
        '''
        loop = loop or asyncio.get_event_loop()
        if isinstance(task, Coroutine):
            task = loop.create_task(task)
        return self.TaskSession._setup_list(task, self)

def stack_varibles(stack_level:int = 0) -> tuple[dict[str, Any], dict[str, Any]]:
    '''
    Get the varibles of the stack
    :param stack_level: the stack level, default is 0, will get the varibles of the caller
    :return: the global varibles and local varibles
    '''
    import inspect
    frame = inspect.currentframe()
    for _ in range(stack_level + 1):
        frame = frame.f_back
    return frame.f_globals, frame.f_locals

def getframe(stack_level:int = 0) -> FrameType:
    '''
    Get the frame
    :param stack_level: the stack level, default is 0, will get the frame of the current function
    '''
    import inspect
    frame = inspect.currentframe()
    for _ in range(stack_level + 1):
        frame = frame.f_back
    return frame

def getcaller(stack_level:int = 1):
    '''
    Get the caller
    '''
    import sys
    frame = getframe(stack_level + 1)
    if '<locals>' in frame.f_code.co_qualname:
        # Unable to get the caller
        return None
    splits = frame.f_code.co_qualname.split('.')
    module = sys.modules[frame.f_globals['__name__']]
    for split in splits:
        module = getattr(module, split)
    return module

def getcallerclass(stack_level:int = 1):
    '''
    Get the root class of the caller

    Note: The class defined here is the deepest class that can be get, if the class defined in a function, it will return the upper class
    '''
    import sys
    frame = getframe(stack_level + 1)
    splits = frame.f_code.co_qualname.split('.')
    module = sys.modules[frame.f_globals['__name__']]
    ret = temp = module
    for split in splits:
        temp = getattr(temp, split)
        if isinstance(temp, type):
            ret = temp
        else:
            break
    if isinstance(ret, type):
        return ret
    # It seems that the caller is a function or a variable
    return None

def getcallerclassinstance(stack_level:int = 1):
    '''
    Get the class instance of the caller
    '''
    rootclass = getcallerclass(stack_level + 1)
    if rootclass == None:
        return None
    caller = getcaller(stack_level + 1)
    frame = getframe(stack_level + 1)
    if caller == None:
        # Unsure, it may be hacked
        if 'self' in frame.f_locals:
            if isinstance(frame.f_locals['self'], rootclass):
                return frame.f_locals['self']
        return None
    if inspect.isfunction(caller):
        # Standard function
        from .typeval import get_signature
        sig = get_signature(caller)
        # The first parameter is the instance
        instname = sig.parameters[0].name
        if instname in frame.f_locals:
            if isinstance(frame.f_locals[instname], rootclass):
                return frame.f_locals[instname]
    # In other cases, it may be a classmethod or staticmethod, which can not get the instance
    return None

def require_module(name:LiteralString):
    '''
    Require a module, else terminate the program
    '''
    import importlib
    try:
        return importlib.import_module(name)
    except ImportError:
        print("Error finding the module %s" % name)
        exit(-1)

def get_inherit_methods(cls: type, method_name: str) -> list[Callable]:
    '''
    Get the method of the class and its base 
    
    Returns
    -------
    list[Callable] This list is ordered by the order of mro, the first is the method of the base class, the last is the method of the class
    '''
    ret = []
    mro = list(cls.mro())
    mro.reverse()
    for base in mro:
        # Method is inherited by the order of mro
        if method_name in base.__dict__:
            ret.append(base.__dict__[method_name])
    return ret
