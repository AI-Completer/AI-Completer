'''
JSON memory
'''

import json
from typing import Iterable, Iterator, Self
import uuid

from aicompleter.memory.base import MemoryItem
from .base import Memory, MemoryItem, Query

class JsonMemory(Memory):
    '''
    Json Memory
    '''
    def __init__(self):
        self._record:dict[uuid.UUID, MemoryItem] = {}

    def get(self, id: uuid.UUID) -> MemoryItem:
        '''
        Get a memory item by id
        '''
        return self._record[id]

    def put(self, param: MemoryItem | Iterable[MemoryItem]):
        '''
        Put a memory item or a list of memory items into memory
        '''
        if isinstance(param, MemoryItem):
            param = [param]
        for item in param:
            if isinstance(item , MemoryItem):
                self._record[item.id] = item
            else:
                raise TypeError(f'Expect MemoryItem, got {type(item)}')
    
    def query(self, query: Query) -> Iterator[MemoryItem]:
        raise NotImplementedError("JsonMemory does not support query")
    
    def delete(self, id: uuid.UUID) -> None:
        '''
        Delete a memory item by id
        '''
        del self._record[id]

    def all(self) -> Iterator[MemoryItem]:
        '''
        Get all the memory items
        '''
        return self._record.values()
    
    def to_json(self) -> list:
        '''
        Convert to json format
        '''
        return [item.to_json() for item in self._record.values()]
    
    @staticmethod
    def from_json(data: list) -> Self:
        '''
        Load from json format
        '''
        ret = JsonMemory()
        for item in data:
            ret.put(MemoryItem.from_json(item))
        return ret

