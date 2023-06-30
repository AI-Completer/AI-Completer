'''
Task Completer
Used to complete the task fully automatically
'''

import asyncio
import json
import time
from typing import Any
from aicompleter import *
from aicompleter.utils import Struct

class TaskCompleter(ai.ChatInterface):
    '''
    AI Executor of the state machine
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commands.add(Command(
            cmd='task',
            callable_groups={'user'},
            overrideable=False,
            callback=self.cmd_task,
        ))
    
    async def cmd_task(self, session: Session, message: Message):
        '''
        Execute a task
        '''
        if not Struct({
                'task': str,
            }).check(message.content.json):
            raise error.FormatError(
                message=message,
                interface=self,
                content='Unrecognized format'
                )
        task = message.content.json['task']
        
        avaliable_commands = Commands()
        avaliable_commands.add(*session.in_handler.get_executable_cmds(self._user))
        
        command_table = "\n".join(
            f'{index+1}: {content}' for index, content in enumerate(
            [f'{command.cmd}: {command.description} ,args: {command.format.json_text if command.format else "<str>"}'
            for command in avaliable_commands] + [
                'agent: Start an agent to help you finish a complicated subtask(support natural language), if the agent is existed, you\'ll talk with the agent directly, otherwise it\'ll create a new agent. args: {"task":<task>,"name":<agent-name>}',
                'stop: Stop this process, with a returned message. args: <message>',
            ])
        )

        agent = ai.agent.Agent(
            chatai = self.ai,
            user = session.id.hex,
            init_prompt=f'''
You are ChatGPT, an AI that do your task automatically.

Commands:
{command_table}

You are talking with a command parser. So you should reply with the json format below:
{{
    "commands":[{{
        "cmd":<command name>,
        "param":<parameters>
    }}]
}}
If you execute commands, you will receive the return value from the command parser.
You can execute multiple commands at once.
Do not reply with anything else.

Your task is:
{task}
Respond in the language of the task.
'''
        )

        def on_call(cmd:str, param:Any):
            return session.asend(Message(
                content=param,
                user=self._user,
                src_interface=self,
            ))
        agent.on_call = on_call
        agent.enable_ask = False
        
        agent.ask("Start the task now")
        await agent.wait()
        return agent.result
        