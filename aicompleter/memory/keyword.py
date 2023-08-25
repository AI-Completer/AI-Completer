'''
Key word analysis
'''

from typing import Optional
from ..utils import require_module

keyBERT = require_module('keybert')
from keybert import KeyBERT
from transformers import BertTokenizer, BertTokenizerFast

class KeyWord:
    '''
    Key word analysis
    '''
    def __init__(self, tokenizer:Optional[BertTokenizer|BertTokenizerFast] = None):
        self._tokenizer = tokenizer
        if tokenizer==None: self._tokenizer = BertTokenizerFast.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        self.model = KeyBERT(self._tokenizer)
        self.extract = self.model.extract_keywords
        self._added_tokens = []
        
    def add_tokens(self, tokens:list[str]):
        '''
        Add tokens to the model
        '''
        self._tokenizer.add_tokens(tokens)
        self.model.model.resize_token_embeddings(len(self._tokenizer))
        self._added_tokens.extend(tokens)

    def del_tokens(self, tokens:list[str]):
        '''
        Delete tokens from the model
        '''
        self._tokenizer.del_tokens(tokens)
        self.model.model.resize_token_embeddings(len(self._tokenizer))
        for token in tokens:
            self._added_tokens.remove(token)

    @property
    def added_tokens(self):
        '''
        Get added tokens
        '''
        return self._added_tokens
    
