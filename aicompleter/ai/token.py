from typing import Optional
import tiktoken

class Encoder:
    '''
    Encoding operations for tokens
    '''
    def __init__(self, *, model:Optional[str] = None, encoding:Optional[str] = None) -> None:
        if model == None and encoding == None:
            raise ValueError("Either model or encoding should be specified")
        if model != None:
            self._enc = tiktoken.encoding_for_model(model)
        else:
            self._enc = tiktoken.get_encoding(encoding)

    def encode(self, token:str) -> list[int]:
        '''Encode token'''
        if not isinstance(token, str):
            # For compatibility with ai.ai
            # TODO: find a better way
            from .ai import ZipContent
            if isinstance(token, ZipContent):
                token = token.zip
            else:
                raise TypeError("token should be str or ZipContent")
        return self._enc.encode(token)

    def decode(self, token:list[int]) -> str:
        '''Decode token'''
        return self._enc.decode(token)
    
    def encode_batch(self, tokens:list[str]) -> list[list[int]]:
        '''Encode tokens'''
        return self._enc.encode_batch(tokens)
    
    def decode_batch(self, tokens:list[list[int]]) -> list[str]:
        '''Decode tokens'''
        return self._enc.decode_batch(tokens)
    
    def limit(self, token:str, max_length:int, from_right:bool = False) -> str:
        '''
        Limit the length of token
        param:
            token: token to be limited
            max_length: max length of token
            from_right: whether to limit/cut from right
        '''
        ret = self.encode(token)
        if len(ret) > max_length:
            ret = ret[:max_length] if from_right else ret[-max_length:]
        return self.decode(ret)

    def getTokenLength(self, token:str) -> int:
        '''Get the length of token'''
        return len(self.encode(token))
    