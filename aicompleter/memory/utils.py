
from typing import Any, Optional, TypeVar
import sentence_transformers as st
import torch
from torch.types import Device
from .base import *

Model = st.SentenceTransformer

class VectexTransformer:
    '''
    This class is used to transform the text (and other thing if possible) into vectors.
    '''
    def __init__(self, model:Model):
        self.model = model

    def transform_text(self, text:str, batch_size: int = 32, device: str = None) -> torch.Tensor:
        '''
        This method is used to transform the text into vectors.
        '''
        return self.model.encode(text, batch_size=batch_size, device=device)
    
    def cpu(self) -> None:
        '''
        This method is used to move the model to cpu.
        '''
        self.model.cpu()

    def cuda(self, device: int | Device | None) -> None:
        '''
        This method is used to move the model to cuda.
        '''
        self.model.cuda(device)

def getMemoryItem(text:str, data:Any, class_:str = 'default'):
    '''
    This method is used to get a MemoryItem object from text.
    '''
    return MemoryItem(vertex=VectexTransformer(st.SentenceTransformer('distilbert-base-nli-mean-tokens')).transform_text(text),
                    class_=class_,
                    data=data)
