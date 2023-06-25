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
            description='Execute python code, the environment and varibles will be persevered in this conversation.',
            format=CommandParamStruct({
                'code': CommandParamElement(name='code', type='str', description='Python code to execute.', tooltip='code'),
                'type': CommandParamElement(name='type', type='str', description='Type of the code, can be "exec" or "eval"(with returns).', tooltip='exec/eval (default to exec)', default='exec')
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
        ret = func(message.content.json['code'], session.data[self.namespace.name]['globals'])
        return ret if message.content.json['type'] == 'eval' else None
