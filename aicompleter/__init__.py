'''
AutoDone-AI
AutoDone is a framework for interaction among AI, human and system.
'''

__version__ = "0.0.1beta"
__author__ = "Li Yan"
__package__ = "aicompleter"
__license__ = "GPLv3"
__description__ = "AutoDone-AI"
# __url__ = ""
# Unknown yet
import os

if bool(os.environ.get("DISABLE_MEMORY", False)) == False:
    from . import (
        memory,
    )

from .config import (
    Config,
    EnhancedDict,
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
    utils,
    log,
    ai,
    implements,
)

del os
