'''
This is the base module of all error in AICompleter
'''
from __future__ import annotations
from .. import log

class BaseException(Exception):
    '''Base Exception for all AICompleter error'''
    def __init__(self,*args:object, **kwargs: object) -> None:
        interface = kwargs.get('interface', None)
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args)
        self.kwargs = kwargs

        self._logger:log.Logger = log.getLogger('Exception', [self.__class__.__name__])
        self._logger.debug(f"Exception raised. interface={interface} parent={self.parent} args={args} kwargs={kwargs}")

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.args} {self.kwargs}>"
    
    def __init_subclass__(cls) -> None:
        if cls.__doc__ == BaseException.__doc__:
            cls.__doc__ = None
        return super().__init_subclass__()
    
    @property
    def interface(self):
        '''Interface'''
        return self.kwargs.get('interface', None)
    
    @property
    def session(self):
        '''Session'''
        return self.kwargs.get('session', None)

class ParamRequired(BaseException):
    '''Param Required'''
    def __init__(self, param:str, *args: object, **kwargs: object) -> None:
        self.param:str = param
        super().__init__(*args, **kwargs)

class Existed(BaseException):
    '''Existed'''

class NotFound(BaseException):
    '''Not Found'''

class InvalidPath(BaseException):
    '''Invalid Path'''
    def __init__(self, path:str, *args: object, **kwargs: object) -> None:
        self.path:str = path
        super().__init__(*args, **kwargs)

class ConversationTimeOut(BaseException):
    '''Conversation Time Out'''

class ReachedMaxMessage(BaseException):
    '''Reached Max Message'''

class Interrupted(BaseException):
    '''Interrupted'''

class AuthorityError(BaseException):
    '''Authority Error'''

class Conflict(BaseException):
    '''Conflict'''
    def __init__(self, reason:str, *args: object, **kwargs: object) -> None:
        super().__init__(reason, *args, **kwargs)

class Failed(BaseException):
    '''Failed'''
    def __init__(self, reason:str, *args: object, **kwargs: object) -> None:
        super().__init__(reason, *args, **kwargs)

__all__ = (
    'BaseException',
    *(
        i.__name__ for i in globals().values() if isinstance(i, type) and issubclass(i, BaseException)
    )
)
