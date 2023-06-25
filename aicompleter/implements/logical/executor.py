import json
import time
import uuid
from typing import Optional

from aicompleter import *
from aicompleter.ai import ChatInterface, ChatTransformer, Conversation
from aicompleter.interface import Command, Commands


class ExecutorInt(ChatInterface):
    '''
    Executor Interface
    This interface will directly analyze the task and call it directly
    '''
    def __init__(self, *, ai: ChatTransformer,user:Optional[str] = None, id: Optional[uuid.UUID] = None):
        super().__init__(ai=ai, namespace='executor', user=user, id=id)
        self.commands.add(
            Command(
                cmd='task-analyze',
                description='Analyze the task, this will split the task into subtasks in natural language',
                expose=True,
                in_interface=self,
                to_return=True,
                force_await=True,
                callback=self.cmd_task_anylyze,
                format=CommandParamStruct({
                    'task': CommandParamElement('task', str, description='The subtask in natural language')
                })
            ),
            Command(
                cmd='execute',
                description='Execute the task in natural language',
                expose=True,
                in_interface=self,
                to_return=True,
                force_await=True,
                callback=self.cmd_execute,
                format=CommandParamStruct({
                    'tasks': [CommandParamElement('task', str, description='The subtask in natural language')]
                })
            )
        )

    async def cmd_task_anylyze(self, session: Session, message: Message) -> list[dict[str, (str, int)]]:
        '''
        Analyze the task, this will split the task into commands in natural language
        '''
        data = EnhancedDict(message.content.json)
        if 'task' not in data:
            raise error.ParamRequired(data, detail='Missing task')
        data.setdefault('enable_detail', False)

        ret = await self.ai.generate_text(
            conversation=Conversation(
                messages=[
                    ai.Message(
                        content='''
You are a task analyzer.
Your task is to analyze the task in natural language and split it into indivisible subtasks.
What the user said is the task.
reply with the json format below(important!):
[{{"task":<str task>, "difficulty":<int difficulty>}},...]
The difficulty is from 1 to 10, 1 means the easiest, 10 means the hardest.
If you think what the user talk is not a task, reply with {"is_task": false}.
If you think the task is not a indivisible subtask, reply with {"undivisible": true, "difficulty": <int difficulty>}.
'''
+ ('If you think the task require more details, reply with {"detail": true}.\n' if data['enable_detail'] else '') +
'''
If one subtask is simple for you, you can apply the result to the next subtask directly or return the result to the user. Use this way to reduce the number of subtasks.
Do not reply with anything else.
                        ''',
                        role='system'
                    ),
                    ai.Message(
                        content=message.content.json['task'],
                        role='user',
                        user=self.user
                    )
                ]
            )
        )

        try:
            ret = json.loads(ret)
        except json.JSONDecodeError:
            raise error.AI_InvalidJSON(ret)
        
        if isinstance(ret, dict):
            # Unexpected result
            if 'is_task' in ret:
                raise error.AI_InvalidTask(ret)
            elif 'undivisible' in ret:
                if 'difficulty' not in ret:
                    raise error.AI_InvalidJSON(ret, detail='Missing difficulty')
                return [{'task': message.content.text, 'difficulty': ret['difficulty']}]
            elif 'detail' in ret:
                raise error.AI_RequireMoreDetail(ret)
            else:
                raise error.AI_InvalidJSON(ret)
        elif isinstance(ret, list):
            # Expected result
            for dictcheck in ret:
                if not isinstance(dictcheck, dict):
                    raise error.AI_InvalidJSON(ret, detail='The json is not a dict')
                if 'task' not in dictcheck:
                    raise error.AI_InvalidJSON(ret, detail='Missing task')
                if 'difficulty' not in dictcheck:
                    raise error.AI_InvalidJSON(ret, detail='Missing difficulty')
                if not isinstance(dictcheck['task'], str):
                    raise error.AI_InvalidJSON(ret, detail='The task is not a str')
                if not isinstance(dictcheck['difficulty'], int):
                    raise error.AI_InvalidJSON(ret, detail='The difficulty is not a int')
            return ret

    async def cmd_execute(self, session: Session, message:Message):
        '''
        Execute the task
        
        This will enforce a logical handling for an abstract task in natural language and execute it.
        '''
        avaliable_commands = Commands(session.in_handler.get_executable_cmds(self._user))
        require_commands = set('execute')
        if require_commands - set(avaliable_commands.keys()):
            raise error.AI_InvalidConfig('Missing required commands: ' + ', '.join(require_commands - set(avaliable_commands.keys())), detail='Missing required commands')
        
        command_table = "\n".join(
            [f'|{command.cmd}|{command.format.json_text}|{command.description}|'
            for command in avaliable_commands] + [
                '|agent|<str task>|Start an agent to help you finish a complicated subtask|\n'
                '|stop|<str message>|Stop this conversation, with a return message. You should call it only when the task is done or when the user require you to do so.|\n'
            ]
        )
        conversation = Conversation(
            messages=[
                ai.Message(
                    content=f'''
You are a task executor. Your goal is to execute the task by the commands.
You can execute commands below:
|Name|Parameter|Description|
|-|-|-|
{command_table}
You need to reply with the json format below(important!):
[{{"cmd": <name>, "param": <parameters>, "async": <bool>"}},...]
You will see the result of the command in the next message if they are not async.
Note: some commands are forcely unasync no matter what you set the async.
Then you can continue to execute the next command.
'''
+  'You should reply user with command.' if 'ask' in avaliable_commands else 'You should not ask user for more details.' +
f'''
Current Time: {time.asctime()}
Do not reply with anything else.
'''
                    ,role='system'
                ),
                ai.Message(
                    content=MultiContent({"tasks":message.content.json['tasks']}),
                    role='user',
                )
            ]
        )
        stop = False
        while not stop:
            reply = await self.ai.generate_text(conversation=conversation)
            conversation.messages.append(ai.Message(
                content=reply,
                role='assistant',
            ))
            session.extra[f'{self.namespace.name}.conversation.{session.id}.data'] = conversation
            result_list = []

            def _set_result_conversation():
                'Set the result and append the conversation'
                conversation.messages.append(ai.Message(
                    content=MultiContent(result_list),
                    role='user',
                ))
            try:
                reply = json.loads(reply)
            except json.JSONDecodeError:
                raise error.AI_InvalidJSON(reply)
            
            # Analyze the reply
            if not isinstance(reply, list):
                raise error.AI_InvalidJSON(reply, detail='The json is not a list')
            for cmdindex, execcmd in enumerate(reply):
                if not isinstance(execcmd, dict):
                    raise error.AI_InvalidJSON(execcmd, detail='The json is not a dict')
                if 'cmd' not in execcmd:
                    raise error.AI_InvalidJSON(execcmd, detail='Missing cmd')
                if 'param' not in execcmd:
                    raise error.AI_InvalidJSON(execcmd, detail='Missing param')
                if 'async' not in execcmd:
                    raise error.AI_InvalidJSON(execcmd, detail='Missing async')
                # Execute
                if execcmd['cmd'] == 'agent':
                    # Call self (ignore the async)
                    self.logger.info("Start a subagent: Task=%s", execcmd['param'])
                    ret = await session.asend(session, Message(
                        content=MultiContent({"task": execcmd['param']}),
                        src_interface=self,
                        dest_interface=self,
                        session=session,
                        cmd='execute',
                    ))
                    result_list.append({'cmd-index': cmdindex, 'result': ret,})
                elif execcmd['cmd'] == 'stop':
                    # Stop the conversation
                    self.logger.info("Stop the conversation: Message=%s", execcmd['param'])
                    result_list.append({'cmd-index': cmdindex, 'result': execcmd['param']})
                    stop=True
                    break
                else:
                    # Call the command
                    if not execcmd['cmd'] in avaliable_commands:
                        # Try tell AI to correct the command
                        result_list.append({'cmd-index': cmdindex, 'error': 'Command not found', 'success': False})
                        _set_result_conversation()
                        break
                    try:
                        ret = (session.send if execcmd['async'] else session.asend)(Message(
                            content=MultiContent(execcmd['param']),
                            src_interface=self,
                            dest_interface=avaliable_commands[execcmd['cmd']],
                            session=session,
                        ))
                        if not execcmd['async']:
                            ret = await ret
                            result_list.append({'cmd-index': cmdindex, 'result': ret, 'success': True})
                        else:
                            result_list.append({'cmd-index': cmdindex, 'called': True})
                    except Exception as e:
                        # TODO: Add more error handling
                        result_list.append({'cmd-index': cmdindex, 'error': str(e), 'success': False})
                        _set_result_conversation()
                        break
        
        # Save conversation
        session.extra[f'{self.namespace.name}.conversation.{session.id}.data'] = conversation
        session.extra[f'{self.namespace.name}.conversation.{session.id}.done'] = True

        return result_list[-1]['result']
