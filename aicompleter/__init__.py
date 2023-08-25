'''
AI-Completer
AI-Completer is a framework for interaction among AI, human and system.
'''

__version__ = "0.0.1rc5"
__author__ = "Li Yan"
__package__ = "aicompleter"
__license__ = "GPL-3.0"
__description__ = "AI-Completer, a framework for interaction among AI, human and system."

import sys
if sys.version_info < (3, 11):
    raise RuntimeError('Python 3.11 or higher is required.')
del sys

from . import (
    common,
    language,
    utils,
)

from .utils import (
    EnhancedDict,
    DataModel,
)

from .config import (
    Config,
    ConfigModel,
)

from .handler import (
    Handler,
)

from .session import (
    Message,
    Session,
    MultiContent,
    Content,
)
from .interface import (
    Interface,
    User,
    Group,
    Command,
    Commands,
    CommandParamElement,
    CommandParamStruct,
    CommandParam,
    CommandAuthority,
)

from .namespace import (
    BaseNamespace, 
    Namespace
)

from .layer import (
    DiGraph,
    InterfaceDiGraph,
)

from . import (
    interface,
    session,
    error,
    config,
    log,
    events,
    ai,
    implements,
)

from . import (
    memory,
)
