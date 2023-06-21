'''
AI Memory
'''
import os

from .base import (
    MemoryItem,
    Query,
    Memory,
    MemoryClass,
)

from .utils import (
    Model,
    VectexTransformer,
    getMemoryItem,
    MemoryConfigure,
)

if bool(os.environ.get('DISABLE_FAISS', False)) == False:
    from .faissimp import (
        FaissMemory,
    )

from .history import (
    HistoryFile,
)
del os
