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
from aicompleter.ai import ChatInterface
from aicompleter.common import deserialize, serialize

class SelfStateExecutor(ChatInterface):
    '''
    AI Executor of the state machine
    '''
    cmdreg = Commands()

    def _gen_agent(self, session: Session):
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
{"commands":[{"cmd":<command>,"param":<parameters>}]}
If you execute commands, you will receive the return value from the command parser.
You can execute multiple commands at once.
User cannot execute the commands or see the result of the commands, they say words and tell you to do the task, 
as a result, rely more on yourself to finish the task.
You should use the "stop" command to stop the conversation.
You can use "$last_result" to refer to the last command result, including the error.
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

Commands:
{command_table}

'''
+  '' if 'ask' in avaliable_commands else 'You should not ask user for more details.' +
'''
You are talking with a command parser. So you should reply with the json format below:
{"commands":[{"cmd":<command>,"param":<parameters>}]}
If you execute commands, you will receive the return value from the command parser.
You can execute multiple commands at once.
User cannot execute the commands or see the result of the commands, they say words and tell you to do the task.
As a result, rely more on yourself to finish the task.
You should use the "stop" command to stop the conversation.
You can use "$last_result" to refer to the last command result, including the error.
Do not reply with anything else.
'''
)
        agent.on_subagent = on_subagent

        data = self.getdata(session)
        data['agent'] = agent

        from ... import language
        # Add default conversation
        agent.conversation.messages.extend([
            ai.Message(
                content = language.DICT[self.getconfig(session).get('language', 'en-us')]['greeting'],
                role='user',
                user=session.id.hex[0:8],
            ),
            ai.Message(
                content = '{"commands":[{"cmd":"ask", "param":{"content":"%s"}}]}' % language.DICT[self.getconfig(session).get('language', 'en-us')]['greeting_reply'],
                role='assistant',
            )
        ])
        return agent
        
    async def session_init(self, session: Session):
        self._gen_agent(session)

    @cmdreg.register(
        'agent',
        'Start an agent to execute a task',
        callable_groups={'user'},
        overrideable=False,
    )
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
        
        await agent.wait()
        return agent.result

    def setStorage(self, session: Session, data: dict):
        conversation = deserialize(data)
        agent = self._gen_agent(session)
        agent.conversation = conversation

    def getStorage(self, session: Session) -> dict:
        return serialize(self.getdata(session)['agent'].conversation)
