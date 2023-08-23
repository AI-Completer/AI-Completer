import asyncio
import json
from typing import Optional
from ... import error, Session, Interface, User, BaseNamespace, Config, Commands, Message, Command, language, ConfigModel
from ...ai.agent import ReAgent
from ...ai import ChatTransformer, Conversation, Message as AIMessage, AuthorType
from ...utils import DataModel

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
        commands.append(Command('stop', 'Stop this conversation with a return'))

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
