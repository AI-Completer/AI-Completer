'''
The error which use defination is not in this file and the standard library
'''

from typing import TypeVar
from .base import *

import aicompleter

Interface = TypeVar('Interface', bound='aicompleter.interface.Interface')
Message = TypeVar('Message', bound='aicompleter.session.Message')
Config = TypeVar('Config', bound='aicompleter.config.Config')
Session = TypeVar('Session', bound='aicompleter.session.Session')
Namespace = TypeVar('Namespace', bound='aicompleter.Namespace')

class BaseAICompleterError(BaseException):
    '''Base AI Completer Error'''

class ConfigureMissing(BaseAICompleterError):
    '''Configure Missing'''
    def __init__(self, configure:str, origin:Config, *args: object, **kwargs: object) -> None:
        self.configure:str = configure
        super().__init__(origin, *args, **kwargs)

class AliasConflict(BaseAICompleterError):
    '''Alias Conflict'''
    def __init__(self, command:str, interface: Interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

class NamespaceConflict(BaseAICompleterError):
    '''
    The namespace have encountered a conflict, may from name conflict, or other problem caused by the inconsistent of the namespaces
    '''
    def __init__(self, namespace:Namespace, *args: object, **kwargs: object) -> None:
        self.namespace = namespace
        super().__init__(*args, **kwargs)

class PermissionDenied(BaseAICompleterError):
    '''Permission Denied'''
    def __init__(self, command:str, interface: Interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

class CommandNotImplement(BaseAICompleterError, NotFound):
    '''Command Not Implement'''
    def __init__(self, command:str, interface: Interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

class MessageNotUnderstood(BaseAICompleterError):
    '''Message Not Understood'''
    def __init__(self, message:Message, interface: Interface, *args: object, **kwargs: object) -> None:
        self.message:Message  = message
        super().__init__(interface = interface, *args, **kwargs)

class FormatError(BaseAICompleterError):
    '''Format Error'''
    def __init__(self, message:Message ,interface: Interface, *args: object, **kwargs: object) -> None:
        self.message:Message  = message
        super().__init__(interface = interface, *args, **kwargs)

class StopHandler(BaseException):
    '''
    Stop Handler
    This exception will stop the handler if raised
    '''
    def __init__(self, message:Message ,interface: Interface, *args: object, **kwargs: object) -> None:
        self.message:Message  = message
        super().__init__(interface = interface, *args, **kwargs)

class Inited(BaseAICompleterError):
    '''Inited'''
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
    
class SessionClosed(BaseAICompleterError):
    '''Session Closed'''
    def __init__(self, session:Session, *args: object, **kwargs: object) -> None:
        self.session:Session = session
        super().__init__(*args, **kwargs)

__all__ = (
    *(
        i.__name__ for i in globals().values() if isinstance(i, type) and issubclass(i, BaseException)
    ),
)
