
import functools
from typing import Any, Callable, Literal, TypeVar, Self
import typing
import inspect

def typecheck(value:Any, type_:type|tuple[type, ...]):
    '''
    Check the type of value. If not, raise TypeError
    '''
    if not isinstance(value, type_):
        raise TypeError(f'{value} is not {type_}')

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

    def check(self, data:Any) -> bool:
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
                if set(struct.keys()) < set(data.keys()):
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
    Note: When passing list, dict, or so on of cantainer type in hooked_vars, you should use a copy
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
