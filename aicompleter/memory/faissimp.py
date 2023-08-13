import contextlib
import os
import uuid
from typing import Callable, Iterable, Iterator, Optional, Self

from .. import utils

# This operation is get the faiss module and do not unload it
faiss = utils.require_module('faiss')
import faiss

import numpy as np
import torch
from transformers import BertModel, BertTokenizer, BertTokenizerFast

from .. import common
from .base import Memory, MemoryItem, Query, QueryResult, QueryResultItem


class FaissMemory(Memory):
    '''
    Faiss Memory
    '''
    def __init__(self, model:BertModel = None, tokenizer:BertTokenizer|BertTokenizerFast = None, index: Optional[faiss.Index] = None) -> None:
        '''
        Initialize Faiss Memory
        '''
        self.model = model
        if model==None: self.model = BertModel.from_pretrained("shibing624/text2vec-base-chinese")
        self.tokenizer = tokenizer
        if tokenizer==None: self.tokenizer = BertTokenizerFast.from_pretrained("shibing624/text2vec-base-chinese")
        self.index = index
        if index==None: self.index:faiss.IndexFlatL2 = faiss.IndexFlatL2(self.model.embeddings.word_embeddings.embedding_dim)
        self._record:list[MemoryItem] = []

    def _encode(self, texts: list[str]) -> torch.Tensor:
        '''
        Encode a text
        '''
        return self.tokenizer(texts, add_special_tokens=True, return_tensors='pt', padding=True)['input_ids']
    
    def _vertex(self, texts: list[str]) -> np.ndarray:
        '''
        Get the vertex of a text
        '''
        ret = self.model(self._encode(texts))
        return np.vstack([ret[0][index][0].detach().numpy().reshape((1,-1)) for index in range(len(texts))])

    def put(self, param: MemoryItem | Iterable[MemoryItem]):
        '''
        Put a memory item or a list of memory items into memory
        '''
        if isinstance(param, MemoryItem):
            param = [param]
        self.index.add(np.array(self._vertex([item.content for item in param])))
        self._record.extend(param)

    def query(self, query: Query) -> QueryResult:
        '''
        Query memory
        '''
        D, I = self.index.search(self._vertex([query.content]), query.limit)
        return QueryResult(query, [QueryResultItem(self._record[i], float(d)) for d, i in zip(D[0], I[0])])

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

    def write_index(self, file:str): 
        faiss.write_index(self.index, file)

    @staticmethod
    def read_index(file:str):
        '''
        Read index from file
        Use this to restore index

        Example:
        
        >>> memory = FaissMemory(..., index=FaissMemory.read_index('index.bin'))
        '''
        return faiss.read_index(file)
    
    def save(self, path: str) -> None:
        with contextlib.suppress(FileExistsError):
            os.mkdir(path)
        torch.save(self.model.state_dict(), os.path.join(path, 'model.pt'))
        self.tokenizer.save_pretrained(path)
        self.write_index(os.path.join(path, 'index.bin'))
        with open(os.path.join(path, 'record.txt'), 'w', encoding='utf-8') as f:
            f.write(common.serialize(self._record))

    @classmethod
    def load(cls, path: str) -> Self:
        model = BertModel.from_pretrained(path)
        tokenizer = BertTokenizerFast.from_pretrained(path)
        index = cls.read_index(os.path.join(path, 'index.bin'))
        with open(os.path.join(path, 'record.txt'), 'r', encoding='utf-8') as f:
            record = common.deserialize(f.read())
        ret = cls(model, tokenizer, index)
        ret._record = record
        return ret
    