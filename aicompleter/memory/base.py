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

from ..common import AttrJSONSerializable, JSONSerializable, Saveable

class MemoryCategory:
    '''
    Memory Category
    '''
    def __init__(self, category: str) -> None:
        self.category = category

    def __eq__(self, o: object) -> bool:
        if isinstance(o, str):
            return self.category == o
        elif isinstance(o, MemoryCategory):
            return self.category == o.category
        else:
            return False
        
    def __str__(self) -> str:
        return self.category
    
    def __repr__(self) -> str:
        return f"MemoryClass({self.category})"
    
    def __hash__(self) -> int:
        return hash(self.category)

@attr.s(auto_attribs=True)
class MemoryItem(AttrJSONSerializable):
    '''
    Memory Item
    '''
    content: str = attr.ib(validator=attr.validators.instance_of(str))
    'The content of the item, this will be encoded into vertex, if possible'
    id: uuid.UUID = attr.ib(factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID))
    'The unique id of the item'
    category: MemoryCategory = attr.ib(default=MemoryCategory('default'), converter=MemoryCategory)
    'The category of the item, usually used for classification for different types of items'
    data: Any = attr.ib(default=None)
    '''
    The data of the item
    Could be dict or list, or any other type with to_json method
    Note: When extracting data from a json file, the data will be a dict, list, string or a Memory object
    '''
    timestamp: float = attr.ib(factory=time.time, validator=attr.validators.instance_of(float))
    'The timestamp of the item'

    @staticmethod
    def deserialize(src: dict) -> Self:
        '''
        Get a MemoryItem from a dict
        '''
        ret = MemoryItem(id=uuid.UUID(src['id']),
                        content=src['content'],
                        category=MemoryCategory(src['category']),
                        timestamp=src['timestamp'])
        if 'data' in src:
            ret.data = src['data']
            try:
                ret.data = json.loads(ret.data)
                if 'type' in ret.data and ret.data['type'] == 'memory':
                    ret.data = Memory.from_json(ret.data)
            except json.JSONDecodeError:
                pass
        return ret
    
    def serialize(self) -> dict:
        '''
        Get a dict from a MemoryItem
        '''
        ret = {
            'id': self.id.hex,
            'content': self.content,
            'category': self.category.category,
            'timestamp': self.timestamp,
        }
        if self.data == None:
            return ret
        if isinstance(self.data, (dict, list)):
            ret['data'] = json.dumps(self.data)
            return ret
        try:
            if hasattr(self.data, 'to_json'):
                ret['data'] = json.dumps(self.data.to_json())
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
    content:str = attr.ib(validator=attr.validators.instance_of(str))
    'The content of the query'
    class_: Optional[str] = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
    'The class of the query, usually used for classification for different types of items'
    limit: int = attr.ib(default=10, validator=attr.validators.instance_of(int), converter=int)
    'The limit of the query'

class Memory(Saveable, JSONSerializable):
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
        raise NotImplementedError(f"Class {self.__class__.__name__} does not support all method")

    def save(self, path:str) -> None:
        '''
        Save the memory to a file
        You can modify this function to support other file format
        '''
        with open(path, 'w') as f:
            json.dump(self.serialize(), f, ensure_ascii=False, indent=4)
    
    @staticmethod
    def load(path:str) -> Self:
        '''
        Load the memory from a file
        You can modify this function to support other file format
        '''
        with open(path, 'r') as f:
            data = json.load(f)
            return Memory.deserialize(data)

@attr.s(auto_attribs=True)
class MemoryConfigure:
    '''
    Configure of the memory
    '''
    factory: type = attr.ib(default=Memory)
    'The factory of the memory'
    factory_args: tuple = attr.ib(default=(), validator=attr.validators.instance_of(tuple))
    'The args of the factory'
    factory_kwargs: dict = attr.ib(default={}, validator=attr.validators.instance_of(dict))
    'The kwargs of the factory'
    initial_memory: Optional[Memory] = attr.ib(default=None)
    'The initial memory of the memory'

    def __attrs_post_init__(self) -> None:
        if self.initial_memory is None:
            self.initial_memory = self.factory(*self.factory_args, **self.factory_kwargs)
    
    @factory.validator
    def check_factory(self, attribute: str, value: type) -> None:
        if not issubclass(value, Memory):
            raise ValueError(f"Factory must be a subclass of Memory.")

    # Check the type of the initial memory
    @initial_memory.validator
    def check_initial_memory(self, attribute: str, value: Optional[Memory]) -> None:
        if value != None and self.factory != value.__class__ and self.factory != None:
            raise ValueError(f"Initial memory must be {self.factory.__name__}.")
