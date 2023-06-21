
from abc import abstractmethod
from typing import Iterable, TypeVar
import aicompleter as aic
# from aicompleter import *

Command = TypeVar('Command', bound='aic.Command')
Commands = TypeVar('Commands', bound='aic.Commands')

class PromptGenerator:
    '''
    Base class for prompt generators.
    '''
    
    @abstractmethod
    def generate(self, *args, **kwargs) -> str:
        '''
        Generate a prompt from the given arguments.
        '''
        pass

class CommandsPromptGenerator(PromptGenerator):
    '''
    Prompt generator for commands.
    '''
    
    @staticmethod
    def generate(self, commands: Commands) -> str:
        '''
        Generate a prompt from the given commands.
        '''
        return '|Command|Format|Description|\n|-|-|-|\n' + '\n'.join(
            f'|{command.cmd}|{command.format.json_text}|{command.description}|'
            for command in commands
        )
    
class ReplyRequireGenerator(PromptGenerator):
    '''
    Prompt generator for reply requires.
    '''

    @staticmethod
    def generate(self, prerequires: Iterable[str]) -> str:
        '''
        Generate a prompt from the given reply requires.
        '''
        return '\n'.join([
            'Reply requires:',
            *prerequires,
        ] + [
            '''
You should reply with the json format below:
[{'cmd': <str cmd>, 'param': <param>}, ...]
Do not reply anything else.
'''])

