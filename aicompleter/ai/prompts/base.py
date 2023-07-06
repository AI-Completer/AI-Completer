
from typing import Literal, Optional, Self
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
    def __init__(self, init_prompt:str, subpromptgenerators:Optional[list[Self]] = None):
        self.init_prompt = init_prompt
        'Initial prompt.'
        self.subpromptgenerators:list[Self] = subpromptgenerators or []
        '''
        Sub prompt generators.
        The sub prompt generators will be used to generate sub prompts.
        '''
    
    def generate(self) -> str:
        '''
        Generate a prompt from the given arguments.
        '''
        ret = self.init_prompt
        if ret:
            ret += '\n'
        ret += '\n'.join(
            generator.generate()
            for generator in self.subpromptgenerators
        )
        return ret

class CommandsPromptGenerator(PromptGenerator):
    '''
    Prompt generator for commands.
    '''
    
    def __init__(self, commands: Commands, format:Literal['table', 'list'] = 'table'):
        super().__init__(init_prompt='Commands:')
        self.commands:aic.Commands = commands
        self.format = format
        if self.format not in ['table', 'list']:
            raise ValueError(f'Invalid format: {self.format}, available formats: table, list')

    def generate(self) -> str:
        '''
        Generate a prompt from the given commands.
        '''
        match self.format:
            case 'table':
                return '|Command|Format|Description|\n|-|-|-|\n' + '\n'.join(
                    f'|{command.cmd}|{command.format.json_text}|{command.description}|'
                    for command in self.commands
                )
            case 'list':
                return '\n'.join(
                    f'{index}. {command.cmd} : {command.description} . args: {command.format.json_text}'
                    for index, command in enumerate(self.commands, start=1)
                )
            case _:
                raise

class ConstantsPromptGenerator(PromptGenerator):
    '''
    Prompt generator for constants.
    '''

    def __init__(self, constants: Iterable[str]):
        super().__init__(init_prompt='')
        self.constants = constants

    def generate(self) -> str:
        '''
        Generate a prompt from the given constants.
        '''
        return '\n'.join(
            constant
            for constant in self.constants
        )

class ReplyRequireGenerator(ConstantsPromptGenerator):
    '''
    Prompt generator for reply requires.
    '''
    def __init__(self):
        super().__init__('Reply requires:' + \
'''
You should reply with the json format below:
[{'cmd': <str cmd>, 'param': <param>}, ...]
Do not reply anything else.
'''
        )
