
from typing import Any, Callable, Literal, TypeVar

def typecheck(value:Any, type_:type):
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

