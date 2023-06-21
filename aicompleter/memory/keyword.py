'''
Key word analysis
'''

from keybert import KeyBERT
from transformers import BertTokenizer

class KeyWord:
    '''
    Key word analysis
    '''
    def __init__(self, model_name='distilbert-base-nli-mean-tokens'):
        self._model_name = model_name
        self._tokenizer = BertTokenizer.from_pretrained(model_name, use_fast=True)
        self.model = KeyBERT(self._tokenizer)
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

    def extract(self, text:str, top_n:int=5, keyphrase_ngram_range:tuple=(1, 1), stop_words:str|list[str]=None):
        '''
        Extract key words from text
        '''
        keywords = self.model.extract_keywords(text, keyphrase_ngram_range=keyphrase_ngram_range, stop_words=stop_words, top_n=top_n)
        return keywords

    @property
    def added_tokens(self):
        '''
        Get added tokens
        '''
        return self._added_tokens
