'''
Read and save the memory to the disk
'''
import json
import os
import time
from typing import Any, Iterator, Self

from aicompleter.common import Saveable

from .base import Memory, MemoryItem, Query
from .. import utils

class MemoryFile(Saveable):
    '''
    Memory File
    
    This will contain all the memory class in a file
    '''
    def __init__(self):
        self._path_record:dict[str, str] = {}
        '''
        Reference from a name to a path
        '''
        self._record:utils.EnhancedDict[str, utils.EnhancedDict | Memory ] = utils.EnhancedDict()
        '''
        Reference from a path to a memory
        '''

    def __getitem__(self, name:str) -> Memory:
        '''
        Get a memory by name
        '''
        return self._record[self._path_record[name]]

    def set(self, name:str, path:str, memory:Memory) -> None:
        '''
        Set a memory
        '''
        self._path_record[name] = path
        self._record[path] = memory

    def __iter__(self) -> Iterator[str]:
        '''
        Iterate all the memory names
        '''
        return self._path_record.keys()
    
    def __contains__(self, name:str) -> bool:
        '''
        Check if a memory exists
        '''
        return name in self._path_record

    def __len__(self) -> int:
        '''
        Get the number of memories
        '''
        return len(self._path_record)

    def to_json(self) -> None:
        def __in_to_json(data):
            if isinstance(data, utils.EnhancedDict):
                return {key: __in_to_json(value) for key, value in data.items()}
            elif isinstance(data, Memory):
                return data.to_json()
            else:
                raise TypeError(f'Expect EnhancedDict or Memory, got {type(data)}')
        return {
            'type': 'memoryfile',
            'data': __in_to_json(self._record),
            'map': self._path_record,
        }

    @staticmethod
    def from_json(data:dict[str, Any]) -> Self:
        '''
        Load from json
        '''
        ret = MemoryFile()
        ret._path_record = data['map']
        def __in_from_json(path, data):
            if path not in ret._path_record:
                # Not a memory
                return {key: __in_from_json(path + '.' + key, value) for key, value in data.items()}
            else:
                # A memory
                memory = Memory.from_json(data)
                return memory
        ret._record = __in_from_json('', data['data'])
        return ret

    def save(self, path:str):
        '''
        Save to a file
        '''
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_json(), f, ensure_ascii=False, indent=4)

    @staticmethod
    def load(path:str) -> Self:
        '''
        Load from a file
        '''
        with open(path, 'r') as f:
            data = json.load(f)
            return MemoryFile.from_json(data)
