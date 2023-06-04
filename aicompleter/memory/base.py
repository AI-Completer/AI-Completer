'''
Base Class for abstracting memory layer
This provide a vertex database interface for the project
'''
import time
import uuid
from abc import abstractmethod
from typing import Any, Optional

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
    id: uuid.UUID = attr.ib(default=uuid.uuid4(), converter=uuid.UUID)
    'The unique id of the item'
    vertex: np.ndarray = attr.ib(converter=np.array)
    'The vertex of the item'
    class_: MemoryClass = attr.ib(default=MemoryClass('default'), converter=MemoryClass, factory=MemoryClass)
    'The class of the item, usually used for classification for different types of items'
    data: Any = attr.ib()
    'The data of the item'
    timestamp: float = attr.ib(default=time.time())
    'The timestamp of the item'

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
    def put(self, item: MemoryItem) -> None:
        '''
        Put a memory item into memory
        '''
        pass

    @abstractmethod
    def delete(self, id: uuid.UUID) -> None:
        '''
        Delete a memory item by id
        '''
        pass

    @abstractmethod
    def query(self, query:Query) -> list[MemoryItem]:
        '''
        Query memory items by vertex and class
        '''
        pass

    @abstractmethod
    def count(self, query:Query) -> int:
        '''
        Count memory items by vertex and class
        '''
        pass
