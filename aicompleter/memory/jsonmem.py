'''
JSON memory
'''

import json
from typing import Iterable, Iterator
import uuid

from aicompleter.memory.base import MemoryItem
from .base import Memory, MemoryItem, Query

class JsonMemory(Memory):
    '''
    Json Memory
    '''
    def __init__(self):
        self._record:map[uuid.UUID] = {}

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
    
    def save(self, path: str) -> None:
        '''
        Save the memory to a file
        '''
        items = self.all()
        # Sort by timestamp
        items = sorted(items, key=lambda x: x.timestamp)
        # Convret to dict
        items = [i.to_dict() for i in items]
        # Save
        with open(path, 'w') as f:
            json.dump(items, f)
    
    @staticmethod
    def load(path: str) -> Memory:
        '''
        Load the memory from a file
        '''
        ret = JsonMemory()
        with open(path, 'r') as f:
            data = json.load(f)
            for item in data:
                ret.put(MemoryItem.from_dict(item))
        return ret
