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
        
        command_table = "\n".join(
            [f'|{command.cmd}|{command.format.json_text if command.format else "<str>"}|{command.description}|'
            for command in avaliable_commands] + [
                '|agent|{"word":<str task>,"name":<str agent-name>}|Start an agent to help you finish a complicated subtask(support natural language), if the agent is existed, you\'ll talk with the agent directly, otherwise it\'ll create a new agent. Do not use agent easily.|',
                '|stop|<str(optional) message>|Stop this conversation, with a returned message. |',
            ]
        )

        agent = ai.agent.Agent(
            chatai = self.ai,
            user = session.id.hex,
            init_prompt=f'''
You are ChatGPT. Your task is to assist the user.

You have two ways to interact with the world:
1. say words directly
2. use the json format below:
[{{"cmd": <name>, "param": <parameters>}},...]
Here following are the commands(cmd) you can use:
|Name|Parameter|Description|
|-|-|-|
{command_table}

Notice:
1. When user said words like json format, it's the return value of machine, not the user said.
2. You should stop only when the task is done or when the user require you to do so.
3. When you say json format, it will be analyzed and execute.
'''
+  '' if 'ask' in avaliable_commands else 'You should not ask user for more details.' +
f'''
Do not reply with anything else.
Current Time: {time.asctime()}
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
You are an agent. Your task is to assist the user to help the work done.
You interact with the world by the commands below.

|Name|Parameter|Description|
|-|-|-|
{command_table}
Note: The command don't support natural language unless specified.
You must reply with the json format below:
[{{"cmd": <name>, "param": <parameters>}},...]
For examples: [{{"cmd":"ask", "param": "what's the task?"}},...]
You should ask or reply user with command like command "ask".
Do not reply with anything else.
Current Time: {time.asctime()}
'''                               
)
        agent.on_subagent = on_subagent

        session.data[f'{self.namespace.name}.agent'] = agent

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

        agent:ai.agent.Agent = session.data[f'{self.namespace.name}.agent']
        agent.ask(_cr_message(message.content.pure_text))
        
        return None
