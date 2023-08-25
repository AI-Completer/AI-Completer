'''
All AI Generate Error

Find a better naming rule for this module
'''

from .base import BaseException

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

class AI_OnRun(AIGenerateError):
    '''
    AI is on run
    '''

__all__ = (
    'AIGenerateError',
    *(
        i.__name__ for i in globals().values() if isinstance(i, type) and issubclass(i, AIGenerateError)
    )
)
