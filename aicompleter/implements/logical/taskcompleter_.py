import asyncio
import json
from typing import Optional
from ... import error, Session, Interface, User, BaseNamespace, Config, Commands, Message, Command, language, ConfigModel
from ...ai.agent import ReAgent
from ...ai import ChatTransformer, Conversation, Message as AIMessage, AuthorType
from ...utils import DataModel

def slim_exception(e: Exception):
    # remove __cause__
    if e.__cause__:
        e.__cause__ = None
    newargs = []
    for i in e.args:
        if isinstance(i, (Message, Interface, Session, Command)):
            pass
        elif isinstance(i, Exception):
            newargs.append(slim_exception(i))
        else:
            newargs.append(i)
    e.args = newargs
    if isinstance(e, error.BaseException):
        # have kwargs
        newkwargs = {}
        for k,v in e.kwargs.items():
            if isinstance(i, (Message, Interface, Session, Command)):
                pass
            elif isinstance(i, Exception):
                newkwargs[k] = slim_exception(v)
            else:
                newkwargs[k] = v
        e.kwargs = newkwargs
    return e

class TaskConfigModel(ConfigModel):
    language:str = 'en-us'

class TaskCompleter(Interface):
    cmdreg:Commands = Commands()
    configFactory = TaskConfigModel

    namespace = BaseNamespace('taskcompleter', 'Task completer')
    def __init__(self, ai: ChatTransformer, user: Optional[User] = None, config: Config = Config()):
        super().__init__(user=user, config=config)
        self.ai = ai
    
    @cmdreg.register('task', 'Complete a task')
    async def task(self, session: Session, message: Message, config: TaskConfigModel):
        commands = list(session.in_handler.get_executable_cmds(self.user))
        # Add command: stop
        commands.append(Command('stop', 'Terminate this conversation with a message'))

        command_table = '\n'.join([
            f"{index}. {command.name}: {command.description}, args: {command.format.json_text if command.format else 'any'}"
            for index, command in enumerate(commands, 1)
        ])

        init_conversation = \
f'''\
You are ChatGPT, a bot trained to preform variuos tasks.

Commands:
{command_table}

Note:
1. You cannot use non-existent commands.
2. You should respond with text in the format `{{"command": <command>, "arguments": <args>}}` to execute the commands.
3. You cannot ask for help from the user or receive their replies.
4. After completing your task, remember to call `stop`. (!important)

Your task:
```
{message.content.text}
```
'''

        agent = ReAgent(self.ai, init_conversation=Conversation([
            AIMessage(init_conversation),
            AIMessage(language.DICT[config.language]['start_task'], role=AuthorType.USER, user=session.id.hex[:8])
        ]))

        @agent.on_response
        async def _(agent:ReAgent, message:AIMessage):
            try:
                try:
                    data = json.loads(message.content)
                except json.JSONDecodeError:
                    # Wrong json format
                    raise ValueError('JSON Parse failed, is your format wrong?')
                command = data['command']
                arguments = data['arguments']

                ret = await session.asend(command, arguments, src_interface=self)

                agent.append_system(json.dumps({
                    'success': True,
                    'result': ret
                }, ensure_ascii=False))
            except Exception as e:
                agent.append_system(json.dumps({
                    'success': False,
                    'error': str(slim_exception(e))
                }, ensure_ascii=False))

        agent.trigger()

        try:
            return await agent
        except Exception as e:
            raise e

class TaskAnalysisAndCaller(Interface):
    '''
    This ai interface will perform a difficult task.
    '''
    cmdreg:Commands = Commands()
    configFactory = TaskConfigModel
    namespace = BaseNamespace('tasker', 'Task analysis and caller')
    def __init__(self, ai: ChatTransformer, user: Optional[User] = None, config: Config = Config()):
        super().__init__(user=user, config=config)
        self.ai = ai

    @cmdreg.register('task', 'Complete a task')
    async def task(self, session: Session, message: Message, config: TaskConfigModel):
        commands = Commands.from_yield(session.in_handler.get_executable_cmds(self.user))
        command_table = '\n'.join([
            f"{index}. {commands[name].name}: {commands[name].description}"
            for index, name in enumerate(commands, 1)
        ])
        # First, analyse the task
        def analyse_task():
            return self.ai.generate_message(Conversation([
            AIMessage(
f'''\
You are functioning as ChatGPT, an AI bot that specializes in task analysis and subdivision.

Commands to utilize:
{command_table}

Please note:
1. The use of non-existing commands is prohibited.
2. Defaulty, you can not get any wanted information from local files unless the task indicate that they exist.

Your duty:
```
{message.content.text}
```

Please subdivide the task into several subtasks and present your response in a json format, as shown below:
[{{"task": <subtask>, "commands":<expected commands to be used demonstrated as a list, may be empty>, "export": <export result to a variable>, "import": <import results from the exported variable as a list>}}]

However, if the task cannot be accomplished with the provided command set or if it doesn't amount to a distinct task, present your reponse in the json format as shown below:
{{"error": "<your error message (in same language as the user)>"}}

Examples:
[{{"task": "Command Testing", "commands": ["test"], "export":"test_result", "import":[]}}]
'''), AIMessage(language.DICT[config.language]['start_analysis'], role=AuthorType.USER, user=session.id.hex[:8])
        ]))
        for _ in range(3):
            try:
                data = json.loads(await analyse_task())
                if 'error' in data: break
                if not isinstance(data, list):
                    raise ValueError('The task should be a list.')
                for i in data:
                    if set(i) != {'task', 'commands', 'export', 'import'}:
                        raise ValueError('The task should be a list of dict with keys: task, commands, export, import.')
                # finish checking
                break
            except:
                pass
        else:
            raise ValueError('Fail to analyse the task, please try again later.')
        if isinstance(data, list) and 'error' in data:
            raise ValueError(data['error'])
        # split the task
        varibles:dict[str, str] = {}
        for index, i in enumerate(data):
            need_commands = Commands(
                commands[name] for name in i['commands']
            )
            # add stop command
            need_commands['stop'] = Command('stop', 'Terminate this conversation, with a return value which will be exported to the variable')
            export_name = i['export']
            export_value = None
            import_dict = {}
            for name in i['import']:
                import_dict[name] = varibles[name]

            base_prompt = \
f'''\
You are ChatGPT, a bot trained to preform variuos tasks.

Commands:
{command_table}

Note:
1. You cannot use non-existent commands.
2. You should respond with text in the format `{{"command": <command>, "arguments": <args>}}` to execute the commands.
3. You cannot ask for help from the user or receive their replies.
4. After completing your task, remember to call `stop`, {
    f'and the return value will be exported to the variable "{export_name}"' if export_name else 'the result will be saved'
}. (!important)
5. Employ the syntax '$variable_name' to reference variables or the result of a prior command. For instance, '$last' is utilized to indicate the outcome of the most recent executed command.

Your task:
```
{i['task']}
```
'''

            if import_dict:
                base_prompt += \
f'''\
Imported variables:
{json.dumps(import_dict, ensure_ascii=False)}
'''
            
            agent = ReAgent(self.ai, init_conversation=Conversation([
                AIMessage(base_prompt),
                AIMessage(language.DICT[config.language]['start_task'], role=AuthorType.USER, user=session.id.hex[:8])
            ]))

            @agent.on_response
            async def _(agent:ReAgent, message:AIMessage):
                try:
                    try:
                        data = json.loads(message.content)
                    except json.JSONDecodeError:
                        # Wrong json format
                        raise ValueError('JSON Parse failed, is your format wrong?')
                    command = data['command']
                    arguments = data['arguments']
                    arguments_str = arguments

                    if not isinstance(command, str):
                        raise ValueError('The command should be a string.')

                    if isinstance(arguments, (list, dict)):
                        arguments_str = json.dumps(arguments, ensure_ascii=False)
                    # replace variables
                    for k,v in import_dict.items():
                        command = command.replace(f'${k}', v)
                        arguments_str = arguments_str.replace(f'${k}', v)
                    if arguments_str != arguments:
                        arguments = json.loads(arguments_str)

                    if command=='stop':
                        agent.set_result(arguments)
                        await agent.close()
                        return

                    ret = await session.asend(command, arguments, src_interface=self)

                    agent.append_system(json.dumps({
                        'success': True,
                        'result': ret
                    }, ensure_ascii=False))
                except Exception as e:
                    agent.append_system(json.dumps({
                        'success': False,
                        'error': str(slim_exception(e))
                    }, ensure_ascii=False))

            agent.trigger()
            try:
                export_value = await agent
            except Exception as e:
                # The bad case, consider to resend the request
                raise e
            if export_name:
                # export_name may be None or '', which means no export
                varibles[export_name] = export_value
        
        # The last export value will be the final result
        return export_value
