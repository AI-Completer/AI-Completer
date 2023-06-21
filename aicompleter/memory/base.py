'''
Base Class for abstracting memory layer
This provide a vertex database interface for the project
'''
from __future__ import annotations

import json
import time
import uuid
from abc import abstractmethod
from typing import Any, Callable, Iterable, Iterator, Optional, Self, overload

import attr
import numpy as np


class MemoryClass:
    '''
    Memory Class
    '''
    def __init__(self, class_: str) -> None:
        self.class_ = class_

    def __eq__(self, o: object) -> bool:
        if isinstance(o, str):
            return self.class_ == o
        elif isinstance(o, MemoryClass):
            return self.class_ == o.class_
        else:
            return False
        
    def __str__(self) -> str:
        return self.class_
    
    def __repr__(self) -> str:
        return f"MemoryClass({self.class_})"
    
    def __hash__(self) -> int:
        return hash(self.class_)

@attr.s
class MemoryItem:
    '''
    Memory Item
    '''
    id: uuid.UUID = attr.ib(factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID))
    'The unique id of the item'
    vertex: np.ndarray = attr.ib(factory=np.array)
    'The vertex of the item'
    class_: MemoryClass = attr.ib(default=MemoryClass('default'), converter=MemoryClass)
    'The class of the item, usually used for classification for different types of items'
    data: Any = attr.ib(default=None)
    'The data of the item'
    timestamp: float = attr.ib(factory=time.time, converter=float)
    'The timestamp of the item'

    @staticmethod
    def from_dict(self, src: dict) -> Self:
        '''
        Get a MemoryItem from a dict
        '''
        ret = MemoryItem(id=uuid.UUID(src['id']),
                        vertex=np.array(src['vertex']),
                        class_=MemoryClass(src['class']),
                        timestamp=src['timestamp'])
        if 'data' in src:
            ret.data = src['data']
            try:
                ret.data = json.loads(ret.data)
            except json.JSONDecodeError:
                pass
        return ret
    
    @classmethod
    def to_dict(self) -> dict:
        '''
        Get a dict from a MemoryItem
        '''
        ret = {
            'id': self.id.hex,
            'vertex': self.vertex.tolist(),
            'class': self.class_.class_,
            'timestamp': self.timestamp,
        }
        if self.data == None:
            return ret
        if isinstance(self.data, (dict, list)):
            ret['data'] = json.dumps(self.data)
            return ret
        try:
            if hasattr(self.data, 'to_dict'):
                ret['data'] = json.dumps(self.data.to_dict())
            else:
                ret['data'] = str(self.data)
        except AttributeError:
            ret['data'] = str(self.data)
        return ret

@attr.s
class Query:
    '''
    Query
    '''
    vertex: np.ndarray = attr.ib(converter=np.array)
    'The vertex of the query'
    class_: Optional[str] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'The class of the query, usually used for classification for different types of items'
    limit: int = attr.ib(default=10, validator=attr.validators.instance_of(int), converter=int)
    'The limit of the query'

class Memory:
    '''
    Memory(Abstraction Layer)
    '''
    @abstractmethod
    def get(self, id: uuid.UUID) -> MemoryItem:
        '''
        Get a memory item by id
        '''
        pass

    @abstractmethod
    @overload
    def put(self, item: MemoryItem) -> None:
        '''
        Put a memory item into memory
        '''
        pass

    @abstractmethod
    @overload
    def put(self, items: Iterable[MemoryItem]) -> None:
        '''
        Put a list of memory items into memory
        '''
        pass

    @abstractmethod
    def put(self, param: MemoryItem | Iterable[MemoryItem]) -> None:
        '''
        Put a memory item or a list of memory items into memory
        '''
        pass

    @abstractmethod
    def delete(self, id: uuid.UUID) -> None:
        '''
        Delete a memory item by id
        '''
        pass

    @abstractmethod
    def query(self, query:Query) -> Iterator[MemoryItem]:
        '''
        Query memory items by vertex and class
        '''
        pass

    def count(self, query:Query) -> int:
        '''
        Count memory items by vertex and class
        '''
        return len(self.query(query))

    def each(self, func: Callable[[MemoryItem],None]) -> None:
        '''
        Iterate all memory items
        '''
        for item in self.all():
            func(item)

    @abstractmethod
    def all(self) -> Iterator[MemoryItem]:
        '''
        Get all memory items
        '''
        pass
