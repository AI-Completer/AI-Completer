'''
An executor fully functional in asyncio
This executor is designed to be a state machine and response with the command
'''

import asyncio
import json
import time
from aicompleter import *
from aicompleter import Session

class StateExecutor(ai.ChatInterface):
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
                # '|agent|{"task":<str task>,"name":<str agent-name>}|Start an agent to help you finish a complicated subtask(support natural language)|',
                '|stop|<str(optional) message>|Stop this conversation, with a returned message. You should call it only when the task is done or when the user require you to do so.|',
            ]
        )

        con = self.ai.new_conversation(user=session.id.hex[:5], init_prompt=
f'''
You are ChatGPT. Your task is to assist the user.
You interact with the world by the commands below.

|Name|Parameter|Description|
|-|-|-|
{command_table}
Note: The command don't support natural language unless specified.
You must reply with the json format below:
[{{"cmd": <name>, "param": <parameters>}},...]
For examples: [{{"cmd":"ask", "param": "what's the task?"}},...]
'''
+  'You should ask or reply user with command like command "ask".' if 'ask' in avaliable_commands else 'You should not ask user for more details.' +
f'''
Do not reply with anything else.
Current Time: {time.asctime()}
'''
        )
        session.data[f'{self.namespace}.conversation'] = con

        return ret

    async def cmd_agent(self, session: Session, message: Message):
        '''
        Start an agent to execute a task
        '''

        def _cr_message(prompt: str|dict|list):
            if isinstance(prompt, str):
                return ai.Message(content=prompt, role='user', user=session.id.hex)
            elif isinstance(prompt, (dict, list)):
                return ai.Message(content=json.dumps(prompt, ensure_ascii=False), role='user', user=session.id.hex)
            raise TypeError(f"Invalid prompt type {type(prompt)}")

        to_execute = await self.ai.ask_once(session.data[f'{self.namespace}.conversation'], _cr_message(message.content.pure_text))
        tasks:dict[tuple[str,str], asyncio.Task] = {}
        task_done_flag = asyncio.Event()
        task_using_lock = asyncio.Lock()
        while True:
            json_dat = None
            async with task_using_lock:
                try:
                    json_dat = json.loads(to_execute)
                except Exception as e:
                    to_execute = await self.ai.ask_once(session.data[f'{self.namespace}.conversation'], _cr_message({'error': 'Invalid json format'}))
                    continue
                if not isinstance(json_dat, list):
                    if isinstance(json_dat, dict):
                        json_dat = [json_dat]
                    else:
                        to_execute = await self.ai.ask_once(session.data[f'{self.namespace}.conversation'], _cr_message({'error': 'Invalid command list format'}))
                        continue
                loop_flag = False
                for cmd in json_dat:
                    if not isinstance(cmd, dict):
                        to_execute = await self.ai.ask_once(session.data[f'{self.namespace}.conversation'], _cr_message({'error': 'Invalid command format'}))
                        loop_flag = True
                        continue
                    if not isinstance(cmd.get('cmd', None), str):
                        to_execute = await self.ai.ask_once(session.data[f'{self.namespace}.conversation'], _cr_message({'error': 'command name not found'}))
                        loop_flag = True
                        continue
                    if not isinstance(cmd.get('param', None), (dict|str)):
                        to_execute = await self.ai.ask_once(session.data[f'{self.namespace}.conversation'], _cr_message({'error': 'command parameters not found'}))
                        loop_flag = True
                        continue
                    if cmd['cmd'] not in (i.cmd for i in session.in_handler.get_executable_cmds(self._user)):
                        if cmd['cmd'] not in ('stop'):
                            to_execute = await self.ai.ask_once(session.data[f'{self.namespace}.conversation'], _cr_message({'error': 'Invalid command'}))
                            loop_flag = True
                            continue
                    if loop_flag:
                        continue
            
            # Check stop command
            if any(cmd['cmd'] == 'stop' for cmd in json_dat):
                # Stop the conversation
                the_cmd = next(cmd for cmd in json_dat if cmd['cmd'] == 'stop')
                if 'param' in the_cmd:
                    return the_cmd['param']
                return None
            
            def _try_parse(x):
                if isinstance(x, dict):
                    return json.dumps(x, ensure_ascii=False)
                return x

            new_tasks = dict(
                ((cmd['cmd'], _try_parse(cmd['param'])),asyncio.get_event_loop().create_task(session.asend(Message(
                    cmd = cmd['cmd'],
                    content = cmd['param'],
                    src_interface=self,
                )))) for cmd in json_dat
            )
            for task in new_tasks.values():
                task.add_done_callback(lambda x: task_done_flag.set())
            
            tasks.update(new_tasks)

            await task_done_flag.wait()

            # Check the done tasks, tell AI and remove them

            async with task_using_lock:
                result_dict = {}
                to_delete = []
                for (cmd, param), task in tasks.items():
                    if task.done():
                        try:
                            ret = task.result()
                        except Exception as e:
                            ret = e
                        result_dict[(cmd, param)] = ret
                        to_delete.append((cmd, param))
                for key in to_delete:
                    del tasks[key]

                to_execute = await self.ai.ask_once(session.data[f'{self.namespace}.conversation'], _cr_message([
                    {'cmd': cmd, 'success': not isinstance(ret, BaseException),'result': ret} for (cmd, param), ret in result_dict.items()
                ]))
            
            task_done_flag.clear()
