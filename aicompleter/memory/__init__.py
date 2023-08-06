'''
AI Memory
'''
from .. import config

from .base import (
    MemoryItem,
    Query,
    Memory,
    MemoryCategory,
    MemoryConfigure,
    Memoryable,
)

# from .utils import (
#     Model,
#     VectexTransformer,
#     getMemoryItem,
# )

# if bool(config.varibles['disable_faiss']) == False:
# from .faissimp import (
#     FaissMemory,
# )

from .jsonmem import (
    JsonMemory,
)

del config
