'''
Task Completer
Used to complete the task fully automatically
'''

import asyncio
import json
import time
from typing import Any, Optional
import uuid
from aicompleter import *
from aicompleter.ai.ai import ChatTransformer
from aicompleter.utils import Struct

class TaskCompleter(ai.ChatInterface):
    '''
    AI Executor of the state machine
    '''
    def __init__(self, ai:ChatTransformer, user:Optional[User] = None, id:uuid.UUID = uuid.uuid4(), config:Config = Config()):
        super().__init__(
            ai = ai,
            namespace='taskcompleter',
            user = user,
            config = config,
            id = id,
        )
        self.commands.add(Command(
            cmd='task',
            description='Execute a task, this will start an agent to help you finish the task, the task must be in natural language, which can easily understand by the AI.',
            callable_groups={'user'},
            overrideable=False,
            callback=self.cmd_task,
            in_interface=self,
            format=CommandParamStruct({
                'task':CommandParamElement(name='task', type=str, optional=False, description='The task to be executed (in natural language), must be a task', tooltip='task')
            })
        ))
    
    async def cmd_task(self, session: Session, message: Message):
        '''
        Execute a task
        '''
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
You should not ask for user's help.

Commands:
{command_table}

What you say is to be parsed by the system. So you should reply with the json format below:
{{
    "commands":[{{
        "cmd":<command name>,
        "param":<parameters>
    }}]
}}
If you execute commands, you will receive the return value from the command parser.
You can execute multiple commands at once.
Do not reply with anything else.
You should execute the "stop" command to finish the task and return the message.
You need to respond in the language of the task.

Your task is:
{task}
'''
        )

        def on_call(cmd:str, param:Any):
            return session.asend(Message(
                content=param,
                cmd=cmd,
                src_interface=self,
            ))
        agent.on_call = on_call
        agent.enable_ask = False
        
        agent.ask("Start the task now")
        await agent.wait()
        return agent.result
        