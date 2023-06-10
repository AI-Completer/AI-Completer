
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

    def transform_text(self, text:str, batch_size: int = 32, device: str = None) -> np.ndarray:
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

@attr.s
class MemoryConfigure:
    '''
    Configure of the memory
    '''
    factory: type = attr.ib(default=Memory, validator=attr.validators.instance_of(Memory))
    'The factory of the memory'
    factory_args: tuple = attr.ib(default=(), validator=attr.validators.instance_of(tuple))
    'The args of the factory'
    factory_kwargs: dict = attr.ib(default={}, validator=attr.validators.instance_of(dict))
    'The kwargs of the factory'
    vertex_model: Model = attr.ib(default=st.SentenceTransformer(), validator=attr.validators.instance_of(Model))
    'The vertex model of the memory'

    initial_memory: Optional[Memory] = attr.ib(default=None)
    'The initial memory of the memory'

    def __attrs_post_init__(self) -> None:
        if self.initial_memory is None:
            self.initial_memory = self.factory(*self.factory_args, **self.factory_kwargs)
    
    # Check the type of the initial memory
    @initial_memory.validator
    def check_initial_memory(self, attribute: str, value: Optional[Memory]) -> None:
        if value != None and self.factory != value.__class__ and self.factory != None:
            raise ValueError(f"Initial memory must be {self.factory.__name__}.")
