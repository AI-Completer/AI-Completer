import uuid
from typing import Any, Coroutine, Optional
from aicompleter.interface.base import User
from aicompleter.interface.command import CommandAuthority
import aicompleter.session as session
from ... import *

class PythonCodeInterface(Interface):
    '''
    This interface is designed to execute python code
    '''
    def __init__(self, config:Config = Config(), id: uuid.UUID = uuid.uuid4()):
        user = User(
            name='pythoncode',
            in_group='system',
            description='Execute python code',
        )
        super().__init__('pythoncode', user, id, config)
        self.commands.add(Command(
            cmd='exec',
            description='Execute python code, the environments and varibles will be persevered in this conversation. You cannot see the stdout directly.',
            format=CommandParamStruct({
                'code': CommandParamElement(name='code', type=str, description='Python code to execute.', tooltip='code'),
                'type': CommandParamElement(name='type', type=str, description='Type of the code, can be "exec" or "eval".', tooltip='exec/eval (default to exec)', default='exec', optional=True)
            }),
            callable_groups={'user','agent'},
            callback=self.cmd_exec,
            authority=CommandAuthority(
                can_execute=True,
            )
        ))

    async def session_init(self, session: Session) -> Coroutine[Any, Any, None]:
        # Create a new globals
        session.data[self.namespace.name]['globals'] = {
            '__name__': '__main__',
            '__doc__': None,
            '__package__': None,
            '__loader__': globals()['__loader__'],
            '__spec__': None,
            '__annotations__': {},
            '__builtins__': __import__('builtins'),
        }

    async def cmd_exec(self, session: Session, message: Message):
        '''
        Execute python code
        '''
        data = self.getdata(session)
        
        func = eval if message.content.json['type'] == 'eval' else exec
        old_dict = dict(data['globals'])
        if func == eval:
            ret = func(message.content.json['code'], old_dict)
            data['globals'] = old_dict
            return ret
        else:
            # exec
            sentences = message.content.json['code'].splitlines()
            if len(sentences) == 1:
                return eval(message.content.json['code'], old_dict)
            if sentences[-1][0] != ' ':
                # Not in a block
                ret = func('\n'.join(sentences[:-1]), old_dict)
                data['globals'] = old_dict
                return eval(sentences[-1], old_dict)
            else:
                # Check the new variables
                old_var = set(old_dict.keys())
                func(message.content.json['code'], old_dict)
                data['globals'] = old_dict
                new_var = set(old_dict.keys())
                if 'result' in (new_var - old_var):
                    return old_dict['result']
        return None
    