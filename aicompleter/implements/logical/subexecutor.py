'''
An executor fully functional in asyncio
This executor is designed to be a state machine and response with the command,
this executor is also designed to be self-called.
'''

import asyncio
import json
import time
from typing import Any, Optional
import uuid
from aicompleter import *
from aicompleter import Session
from aicompleter.ai.ai import ChatTransformer

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
            in_interface=self,
        ))
        
    async def session_init(self, session: Session):
        ret = await super().session_init(session)

        avaliable_commands = Commands()
        avaliable_commands.add(*session.in_handler.get_executable_cmds(self._user))
        
        command_table = "\n".join(
            f'{index+1}: {content}' for index, content in enumerate(
            [f'{command.cmd}: {command.description} ,args: {command.format.json_text if command.format else "<str>"}'
            for command in avaliable_commands] + [
                'agent: Start an agent to help you finish a complicated subtask(support natural language), if the agent is existed, you\'ll talk with the agent directly, otherwise it\'ll create a new agent. args: {"task":<task>,"name":<agent-name>}',
                'stop: Stop this conversation, with a returned message. args: <message>',
            ])
        )

        agent = ai.agent.Agent(
            chatai = self.ai,
            user = session.id.hex,
            init_prompt=
f'''You are ChatGPT, an AI assisting the user.

Commands:
{command_table}

'''
+  '' if 'ask' in avaliable_commands else 'You should not ask user for more details.' +
'''
You are talking with a command parser. So you should reply with the json format below:
{
  "commands":[{
    "cmd":<command name>,
    "param":<parameters>
  }]
}
If you execute commands, you will receive the return value from the command parser.
You can execute multiple commands at once.
User cannot execute the commands or see the result of the commands, they say words and tell you to do the task.
You should use the "ask" command to ask or reply user.
Do not reply with anything else.
'''
        )
        async def on_call(cmd:str, param:Any):
            return await session.asend(Message(
                cmd=cmd,
                content=param,
                src_interface=self,
            ))
        agent.on_call = on_call

        def on_subagent(name:str, word:str):
            agent.new_subagent(name, word, init_prompt=\
f'''
You are an agent. Your task is to assist another AI.

Abalities:
1. You can interact with user by the commands below.
2. You cannot connect to the internet.

Commands:
{command_table}

'''
+  '' if 'ask' in avaliable_commands else 'You should not ask user for more details.' +
'''
You are talking with a command parser. So you should reply with the json format below:
{
  "commands":[{
    "cmd":<command name>,
    "param":<parameters>
  }]
}
If you execute commands, you will receive the return value from the command parser.
You can execute multiple commands at once.
User cannot execute the commands or see the result of the commands, they say words and tell you to do the task.
You should use the "ask" command to ask or reply user.
Do not reply with anything else.
'''
)
        agent.on_subagent = on_subagent

        data = self.getdata(session)
        data['agent'] = agent

        return ret

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
