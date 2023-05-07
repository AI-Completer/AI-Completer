'''
Utils for autodone
'''
from __future__ import annotations
import sys
import asyncio
from typing import Any, Callable

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

async def ainput(string: str = "") -> str:
    '''
    Async input
    '''
    await _on_reading.acquire()
    await asyncio.get_event_loop().run_in_executor(
            None, lambda s=string: sys.stdout.write(s))
    ret = await asyncio.get_event_loop().run_in_executor(
            None, sys.stdin.readline)
    _on_reading.release()
    return ret

async def aprint(string: str) -> None:
    '''
    Async print
    '''
    await _on_reading.acquire()
    await asyncio.get_event_loop().run_in_executor(
            None, lambda s=string: sys.stdout.write(s))
    _on_reading.release()

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
    })
    '''
    def _check_struct(self, struct:dict|list) -> None:
        '''
        Check struct
        '''
        if not isinstance(struct, (dict, list)):
            raise TypeError('struct must be dict or list')
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
        if isinstance(struct, list):
            if len(struct) != 1:
                raise TypeError('list must have only one element')
            for item in struct:
                self._check_struct(item)
        
    def __init__(self ,struct:dict|list) -> None:
        self.struct = struct
        self._check_struct(struct)

    def check(self, data:dict|list) -> bool:
        '''
        Check data
        '''
        def _check(struct:dict|list|type|Callable, data:Any) -> bool:
            if isinstance(struct, dict):
                if not isinstance(data, dict):
                    return False
                for key in struct:
                    if key not in data:
                        return False
                    if not _check(struct[key], data[key]):
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
                return isinstance(data, struct)
            if callable(struct):
                return struct(data)
            raise TypeError('struct must be dict or list or type or callable')
        
        return _check(self.struct, data)

    
