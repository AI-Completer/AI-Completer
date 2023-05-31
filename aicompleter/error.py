from __future__ import annotations

import os
from typing import TypeVar

import aicompleter

from . import log

Interface = TypeVar('Interface', bound='aicompleter.interface.Interface')
Message = TypeVar('Message', bound='aicompleter.session.Message')
Config = TypeVar('Config', bound='aicompleter.config.Config')

class BaseException(Exception):
    '''Base Exception for all Autodone-AI error'''
    def __init__(self,*args:object, **kwargs: object) -> None:
        self.interface = kwargs.pop('interface', None)
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args)
        self.kwargs = kwargs
        self._logger:log.Logger = log.Logger('Exception')
        formatter = log.Formatter([self.__class__.__name__])
        _handler = log.ConsoleHandler()
        _handler.formatter = formatter
        self._logger.addHandler(_handler)
        if os.environ.get('DEBUG', False):
            self._logger.setLevel(log.DEBUG)
        else:
            self._logger.setLevel(log.INFO)
        self._logger.debug(f"Exception raised. interface={self.interface} parent={self.parent} args={args} kwargs={kwargs}")

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.args} {self.kwargs}>"

class ParamRequired(BaseException):
    '''Param Required'''
    def __init__(self, param:str, *args: object, **kwargs: object) -> None:
        self.param:str = param
        super().__init__(*args, **kwargs)

class Existed(BaseException):
    '''Existed'''

class NotFound(BaseException):
    '''Not Found'''

class ConfigureMissing(BaseException):
    '''Configure Missing'''
    def __init__(self, configure:str,origin:Config, *args: object, **kwargs: object) -> None:
        self.configure:str = configure
        super().__init__(origin, *args, **kwargs)

class AliasConflict(BaseException):
    '''Alias Conflict'''
    def __init__(self, command:str, interface: Interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

class PermissionDenied(BaseException):
    '''Permission Denied'''
    def __init__(self, command:str, interface: Interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

class CommandNotImplement(NotFound):
    '''Command Not Implement'''
    def __init__(self, command:str, interface: Interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

class MessageNotUnderstood(BaseException):
    '''Message Not Understood'''
    def __init__(self, message:Message, interface: Interface, *args: object, **kwargs: object) -> None:
        self.message:Message  = message
        super().__init__(interface = interface, *args, **kwargs)

class FormatError(BaseException):
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

class InvalidPath(BaseException):
    '''Invalid Path'''
    def __init__(self, path:str, *args: object, **kwargs: object) -> None:
        self.path:str = path
        super().__init__(*args, **kwargs)

class Inited(BaseException):
    '''Inited'''
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
    

################## AI Generate Error ##################
# AI Generate Error (or possiblily human input error)

class AIGenerateError(BaseException):
    '''
    AI Generate Error
    
    :param content: the content that AI generated
    '''
    def __init__(self, content:str, *args: object, **kwargs: object) -> None:
        self.content:str = content
        super().__init__(*args, **kwargs)

class AI_InvalidJSON(AIGenerateError):
    '''
    What AI generated is not a invalid JSON
    '''

class AI_InvalidTask(AIGenerateError):
    '''
    What AI generated is not a valid task
    '''

class AI_RequireMoreDetail(AIGenerateError):
    '''
    What AI generated is not a valid task
    '''

class AI_InvalidConfig(AIGenerateError):
    '''
    AI is not in a valid config
    This is an exception that caused by configure error
    '''

__all__ = (
    i.__class__.__name__ for i in globals().values() if isinstance(i, BaseException)
)
