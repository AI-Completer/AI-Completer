'''
AutoDone-AI
AutoDone is a framework for interaction among AI, human and system.
'''

__version__ = "0.0.1beta"
__author__ = "Li Yan"
__package__ = "autodone"
__license__ = "MIT"
__description__ = "AutoDone-AI"
# __url__ = ""
# Unknown yet

from . import (
    implements,
    interface,
    session,
    error,
    config,
    utils,
    log,
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
    CommandSet,
    CommandParamElement,
    CommandParamStruct,
)
