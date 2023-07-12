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
    
    def serialize(self) -> dict:
        '''
        Convert to json format
        '''
        return {
            'type': 'memory',
            'subtype': 'jsonmemory',
            'data': [item.serialize() for item in self._record.values()],
        }
    
    @staticmethod
    def deserialize(data: dict) -> Self:
        '''
        Load from json format
        '''
        if data['type'] != 'memory':
            raise ValueError(f"Expect type 'memory', got '{data['type']}'")
        if data['subtype'] != 'jsonmemory':
            raise ValueError(f"Expect subtype 'jsonmemory', got '{data['subtype']}'")
        ret = JsonMemory()
        for item in data['data']:
            ret.put(MemoryItem.deserialize(item))
        return ret
