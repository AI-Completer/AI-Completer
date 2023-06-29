import uuid
from typing import Any, Coroutine, Optional
from aicompleter.interface.base import User
import aicompleter.session as session
from .. import *

class PythonCodeInterface(Interface):
    '''
    This interface is designed to execute python code
    '''
    def __init__(self, user: Optional[User] = None, namespace: str = 'pythoncode', id: uuid.UUID = ...):
        user = user or User(
            name='pythoncode',
            in_group='system',
            description='Execute python code',
        )
        super().__init__(user, namespace, id)
        self.commands.add(Command(
            cmd='exec',
            description='Execute python code, the environments and varibles will be persevered in this conversation.',
            format=CommandParamStruct({
                'code': CommandParamElement(name='code', type=str, description='Python code to execute.', tooltip='code'),
                'type': CommandParamElement(name='type', type=str, description='Type of the code, can be "exec" or "eval".', tooltip='exec/eval (default to exec)', default='exec', optional=True)
            }),
            callable_groups={'user','agent'},
            force_await=True,
            to_return=True,
            callback=self.cmd_exec,
        ))

    async def session_init(self, session: Session) -> Coroutine[Any, Any, None]:
        ret = await super().session_init(session)
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
        func = eval if message.content.json['type'] == 'eval' else exec
        old_dict = dict(session.data[self.namespace.name]['globals'])
        if func == eval:
            ret = func(message.content.json['code'], old_dict)
            session.data[self.namespace.name]['globals'] = old_dict
            return ret
        else:
            # exec
            sentences = message.content.json['code'].splitlines()
            if sentences[-1][0] != ' ':
                # Not in a block
                ret = func('\n'.join(sentences[:-1]), old_dict)
                session.data[self.namespace.name]['globals'] = old_dict
                return eval(sentences[-1], old_dict)
            else:
                # Check the new variables
                old_var = set(old_dict.keys())
                func(message.content.json['code'], old_dict)
                session.data[self.namespace.name]['globals'] = old_dict
                new_var = set(old_dict.keys())
                if 'result' in (new_var - old_var):
                    return old_dict['result']
        return None
    