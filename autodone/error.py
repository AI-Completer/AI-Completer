

from autodone import interface


class BaseException(Exception):
    '''Base Exception for all Autodone-AI error'''
    def __init__(self,*args:object, **kwargs: object) -> None:
        self.interface = kwargs.popitem('interface', None)
        self.parent = kwargs.popitem('parent', None)
        super().__init__(*args)
        self.kwargs = kwargs

class ParamRequired(BaseException):
    '''Param Required'''
    def __init__(self, param:str, *args: object, **kwargs: object) -> None:
        self.param:str = param
        super().__init__(*args, **kwargs)

# class CommandNotFound(BaseException):
#     '''Command not found when call interface commands'''
#     def __init__(self, command:str, interface: interface,*args:object , **kwargs: object) -> None:
#         self.command:str = command
#         super().__init__(interface = interface,*args, **kwargs)

class Existed(BaseException):
    '''Existed'''

class NotFound(BaseException):
    '''Not Found'''

class AliasConflict(BaseException):
    '''Alias Conflict'''
    def __init__(self, command:str, interface: interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

class PermissionDenied(BaseException):
    '''Permission Denied'''
    def __init__(self, command:str, interface: interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

class CommandNotImplement(NotFound):
    '''Command Not Implement'''
    def __init__(self, command:str, interface: interface, *args: object, **kwargs: object) -> None:
        self.command:str = command
        super().__init__(interface = interface, *args, **kwargs)

