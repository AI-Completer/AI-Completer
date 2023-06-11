import uuid
from typing import Callable, Iterable, Iterator, Optional

import faiss
import numpy as np

from .base import Memory, MemoryItem, Query


class FaissMemory(Memory):
    '''
    Faiss Memory
    '''
    def __init__(self, dim: int, index: Optional[faiss.Index] = None) -> None:
        '''
        Initialize Faiss Memory
        '''
        self.dim = dim
        self.index = index or faiss.IndexFlatL2(dim)
        self._record:list[MemoryItem] = []

    def put(self, param: MemoryItem | Iterable[MemoryItem]):
        '''
        Put a memory item or a list of memory items into memory
        '''
        if isinstance(param, MemoryItem):
            param = [param]
        self.index.add(np.array([item.vertex for item in param]))
        for item in param:
            self._record.append(item)

    def query(self, query: Query) -> Iterator[MemoryItem]:
        '''
        Query memory
        '''
        _, I = self.index.search(np.array([query.vertex]), query.limit)
        for i in I[0]:
            yield self._record[i]

    def get(self, id: uuid.UUID) -> MemoryItem:
        '''
        Get a memory item by id
        '''
        for item in self._record:
            if item.id == id:
                return item
        raise KeyError(f'No such item with id {id}')

    def delete(self, id: uuid.UUID) -> None:
        '''
        Delete a memory item by id
        '''
        for i, item in enumerate(self._record):
            if item.id == id:
                del self._record[i]
                break
        else:
            raise KeyError(f'No such item with id {id}')
        self.index.remove_ids(np.array([i]))

    def __len__(self) -> int:
        '''
        Get the length of the memory
        '''
        return len(self._record)

    def all(self) -> Iterator[MemoryItem]:
        '''
        Iterate all memory items
        '''
        yield from self._record
