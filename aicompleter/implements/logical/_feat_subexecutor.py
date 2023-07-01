'''
An executor fully functional in asyncio
This executor is designed to be a state machine and response with the command,
this executor is also designed to be self-called.
'''

import asyncio
import json
import time
from typing import Any

from aicompleter import *
from aicompleter import Session

class SelfStateExecutor(ai.ChatInterface):
    '''
    AI Executor of the state machine
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commands.add(Command(
            cmd='agent',
            callable_groups={'user'},
            overrideable=False,
            callback=self.cmd_agent,
        ))
        
    async def session_init(self, session: Session):
        ret = await super().session_init(session)

        avaliable_commands = Commands()
        avaliable_commands.add(*session.in_handler.get_executable_cmds(self._user))
        
        agent = ai.agent.AgentF(
            chatai = self.ai,
            commands = avaliable_commands,
            user = session.id.hex[:8],
            init_prompt=\
'''
You are ChatGPT, your task is to meet the user's need.
'''
        )

        session.data[self.namespace.name]['agent'] = agent

    async def cmd_agent(self, session: Session, message: Message):
        '''
        Start an agent to execute a task
        '''
        def _cr_message(prompt: str|dict|list):
            if isinstance(prompt, str):
                return prompt
            elif isinstance(prompt, (dict, list)):
                return json.dumps(prompt, ensure_ascii=False)
            raise TypeError(f"Invalid prompt type {type(prompt)}")

        agent:ai.agent.Agent = self.getdata(session)['agent']
        agent.ask(_cr_message(message.content.pure_text))
        
        return None
