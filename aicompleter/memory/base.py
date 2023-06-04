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


@attr.s
class MemoryItem:
    '''
    Memory Item
    '''
    id: uuid.UUID = attr.ib(default=uuid.uuid4(), converter=uuid.UUID)
    'The unique id of the item'
    vertex: np.ndarray = attr.ib(converter=np.array)
    'The vertex of the item'
    class_: str = attr.ib(default='default')
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
    class_: Optional[str] = attr.ib(default=None)
    'The class of the query, usually used for classification for different types of items'
    limit: int = attr.ib(default=10)
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
