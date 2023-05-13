'''
Utils for autodone
'''
from __future__ import annotations
import sys
import asyncio
from typing import Any, Callable, Literal, TypeVar
from concurrent.futures import ThreadPoolExecutor

class defaultdict(dict):
    '''
    Dict that can automatically create new keys
    '''
    def __missing__(self, key):
        self[key] = defaultdict()
        return self[key]

_on_reading:asyncio.Lock = asyncio.Lock()
'''
Global asyncio lock for console input
'''

async def ainput(prompt: str = "") -> str:
    with ThreadPoolExecutor(1, "AsyncInput") as executor:
        return (await asyncio.get_event_loop().run_in_executor(executor, input, prompt)).rstrip()

async def aprint(string: str) -> None:
    '''
    Async print
    '''
    await _on_reading.acquire()
    print(string)
    _on_reading.release()

StructType = TypeVar('StructType', dict, list, type, Callable, tuple)
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

    
