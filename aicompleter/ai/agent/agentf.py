'''
AI Agent With Function

Depreciated, use Agent instead
'''

import asyncio
import copy
import json
import traceback
from typing import Any, Callable, Coroutine, Literal, Optional, Self, overload

from ... import *
from .. import *
from ... import events

# Not using the stream ask due to the structural conversation
class AgentF:
    '''
    AI Agent With Function
    '''
    def __init__(self, chatai: ChatTransformer, init_prompt:str, commands:Commands,  user:Optional[str] = None, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.ai = chatai
        self._init_prompt = init_prompt
        self._loop = loop or asyncio.get_event_loop()
        
        self.conversation = self.ai.new_conversation(user,init_prompt=init_prompt)
        '''The conversation of the agent'''
        self.on_call: Callable[[str, Any], Coroutine[Any, None, None]] = None
        '''Event when a command is called'''
        self.on_subagent: Callable[[str, Any], None | Coroutine[None, None, None]] = lambda name, word: self.new_subagent(name, word)
        '''Event when a subagent is created'''
        self.on_exception: events.Event = events.Event(callbacks=[lambda e: print(traceback.format_exc())])
        '''Event when an exception is raised'''
        # Ask is needed for agents with function when it can be called aside with current message struct
        # self.enable_ask = True
        # '''Enable the ask command'''

        self._raw_commands = commands
        self._commands = copy.copy(commands)
        '''The commands of the agent'''
        self._commands.remove('ask')
        self._commands.remove('echo')

        # Add agent command
        self._commands.add(Command(
            cmd='agent',
            description='Create a subagent to help finish the task, if the subagent is already created, you can speak to it directly, you should not use this command easily',
            expose=True,
            in_interface=None,
            callback=None,
            format = CommandParamStruct({
                'name':CommandParamElement('name', str, 'The name of the subagent'),
                'task':CommandParamElement('task', str, 'The task of the subagent'),
            })
        ), Command(
            cmd='stop',
            description='Stop this conversation, and return the result',
            expose=True,
            in_interface=None,
            callback=None,
            format = CommandParamStruct({
                'result':CommandParamElement('result', object, 'The result of the result'),
            })
        ))

        def get_parameter(cmd: Command):
            def map_type(_type: type) -> str:
                return {
                    str: 'string',
                    int: 'integer',
                    float: 'float',
                    bool: 'boolean',
                    object: 'object',
                }[_type]
            
            if isinstance(cmd.format, CommandParamStruct):
                # TODO : Structizing support
                return [FuncParam(
                    name = param.name,
                    description = param.description,
                    type = map_type(param.type),
                    required = not param.optional,
                ) for param in cmd.format.values()]
            else:
                return []

        self.conversation.functions = [
            Function(
                name=cmd.cmd,
                description = cmd.description,
                parameters = get_parameter(cmd),
            ) for cmd in self._commands
        ]

        self._request_queue: asyncio.Queue[ai.Message] = asyncio.Queue()
        self._loop_task = self._loop.create_task(self._handle_loop())

        self._result = ...

        self._subagents:dict[str, Self] = {}

        self._parent:Optional[Self] = None
        self._parent_name = None

        def _getstruct(value:Self):
            if value._parent:
                return [*_getstruct(value._parent), value._parent_name]
            return [value.ai.name]
        self.logger = log.getLogger('Agent', _getstruct(self))

        self._loop_task.add_done_callback(self._unexception)

        self._stop_event = asyncio.Event()

    def _unexception(self,x:asyncio.Future):
        try:
            x.result()
        except asyncio.CancelledError as e:
            pass
        except Exception as e:
            self._loop.create_task(self.on_exception(e))

    @property
    def stopped(self) -> bool:
        '''
        Whether the agent is stopped
        '''
        return self._stop_event.is_set()
    
    @property
    def result(self) -> Any:
        '''
        The result of the agent
        '''
        if not self.stopped:
            raise RuntimeError('The agent is not stopped yet')
        return self._result

    def new_subagent(self, name:str, init_words: str,init_prompt:Optional[str] = None, ai: Optional[ChatTransformer] = None , user:Optional[str] = None) -> Self:
        '''
        Create a subagent
        '''
        self._subagents[name] = self.__class__(ai or self.ai, init_prompt or self._init_prompt, self._raw_commands, user)
        self._subagents[name].on_call = self.on_call
        self._subagents[name]._parent = self
        self._subagents[name]._parent_name = name
        self._subagents[name].ask(init_words)
        self.logger.debug(f'Create subagent {name}')
        return self._subagents[name]

    def _request(self, value:dict, role:str = 'system'):
        '''
        Ask the agent to execute a command
        '''
        from ... import ai
        self._request_queue.put_nowait(ai.Message(
            content = json.dumps(value, ensure_ascii = False),
            user=self.conversation.user,
            role=role,
        ))

    async def _handle_loop(self):
        '''
        The loop for the agent
        '''
        from ... import ai
        stop_flag = False
        to_raise = None
        try:
            while not stop_flag:
                # Get all the requests
                requests:list[ai.Message] = [await self._request_queue.get()]
                while not self._request_queue.empty():
                    requests.append(self._request_queue.get_nowait())

                self.logger.debug(f'Get requests: {requests}')

                def _try_parse(x:Any):
                    if not isinstance(x, str):
                        return x
                    # Check variable and int and float
                    if all(i in '0123456789.abcefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_' for i in x):
                        return x
                    try:
                        return json.loads(x)
                    except Exception:
                        return x

                if len(requests) == 1:
                    raw_content = _try_parse(requests[0].content)
                    if isinstance(raw_content, dict):
                        raw_content = json.dumps(raw_content, ensure_ascii = False)
                else:
                    raw_content = json.dumps([_try_parse(request.content) for request in requests], ensure_ascii = False)

                new_message = ai.Message(
                    content = raw_content,
                    role = 'user',
                    user = self.conversation.user,
                )
                self.conversation.messages.append(new_message)

                new_message = await self.ai.generate_message(conversation = self.conversation)
                self.conversation.messages.append(new_message)

                raw = new_message.content
                self.logger.debug(f'AI response content: {raw}')

                # Only one of function call and text will be meaningful 

                def call_cmd(name:str, param: Any):
                    def when_result(x: asyncio.Future):
                        try:
                            ret = x.result()
                        except asyncio.CancelledError:
                            return
                        except Exception as e:
                            self._request_queue.put_nowait(ai.Message(
                                content = f'Function Error: {str(e)}',
                                role = 'system',
                            ))
                            self.logger.error(f'Exception when executing command {name}: {e.__class__.__name__}: {e}')
                        else:
                            self._request_queue.put_nowait(ai.Message(
                                content = str(ret),
                                role = 'function',
                                user = name,
                            ))
                            self.logger.info(f'Command {name} executed successfully, Result: {ret}')

                    self._loop.create_task(self.on_call(name, param)).add_done_callback(when_result)

                if new_message.data.get('function_call') == None:
                    # Ask Command
                    self.logger.debug(f'Text: {new_message.content}')
                    call_cmd('ask', {'content':new_message.content})
                else:
                    # The message is a function call
                    self.logger.debug(f'Function call: {new_message.data["function_call"]}')
                    function_call = new_message.data['function_call']
                    
                    if isinstance(function_call, str):
                        function_call = _try_parse(function_call)
                    try:
                        func_name = function_call['name']
                        func_param = json.loads(function_call['arguments'])
                    except Exception as e:
                        if func_name in self._commands:
                            self._request_queue.put_nowait(ai.Message(
                                content = f'Function Parse Error: {str(e)}, May you check your parameters format? This is the format:' + \
                                    self._commands[func_name].format.json_text, # TODO: Format imply
                                role = 'system',
                            ))
                            self.logger.error(f'Exception when parsing function call: {e}')
                            continue

                    try:
                        if func_name == 'stop':
                            stop_flag = True
                            self._result = func_param['result']
                            if self._parent:
                                self._parent._subagents.pop(self._parent_name)
                            continue
                        if func_name == 'agent':
                            # Create a subagent
                            if not all(i in func_param for i in ('name', 'task')):
                                self._request({
                                    'type':'error',
                                    'value':f"Paremeters 'name' and 'word' are required"
                                })
                            if func_param['name'] in self._subagents:
                                self._subagents[func_param['name']].ask(func_param['task'])
                                continue
                            ret = self.on_subagent(func_param['name'], func_param['task'])
                            if asyncio.iscoroutine(ret):
                                await ret
                            continue
                    except KeyError as e:
                        self._request_queue.put_nowait(ai.Message(
                            content = f'Function Parse Error: {str(e)}',
                            role = 'system',
                        ))
                        self.logger.error(f'Exception when parsing function call: {e}')
                        continue
                    except Exception as e:
                        self._request_queue.put_nowait(ai.Message(
                            content = f'Function Error: {str(e)}',
                            role = 'system',
                        ))
                        self.logger.error(f'Exception when executing function call: {e}')
                        continue
                    
                    if func_name not in self._raw_commands:
                        self._request_queue.put_nowait(ai.Message(
                            content = f'Function Parse Error: Function {func_name} not found, your available functions are: {[*self._commands.keys()]}',
                            role = 'system',
                        ))
                        self.logger.error(f'Exception when parsing function call: Not found function {func_name}')
                        continue

                    call_cmd(func_name, func_param)

        except asyncio.CancelledError as e:
            to_raise = e
        finally:
            # The loop is done
            self._loop_task.remove_done_callback(self._unexception)
            self._handle_task = None
            self._loop_task = None
            self._stop_event.set()
            self.logger.debug('The agent is stopped')
            if to_raise != None:
                raise to_raise
            
    def _subagent_ask(self, name:str, value:str):
        '''
        Ask the agent to execute a command
        '''
        self.logger.debug(f'The subagent[{name}] ask: {value}')
        self._request({
            'type':'event',
            'event': 'ask-from-subagent',
            'name': name,
            'value': value,
        })

    def ask(self, value:str):
        '''
        Ask the agent to execute a command
        '''
        self.logger.debug(f'Ask: {value}')
        self._request_queue.put_nowait(ai.Message(
            content = value,
            role = 'user',
            user = self.conversation.user,
        ))

    def wait(self) -> Coroutine[Any, Any, Literal[True]]:
        '''
        Wait until the agent is stopped
        '''
        return self._stop_event.wait()

    def __del__(self):
        if '_loop_task' in self.__dict__ and self._loop_task:
            self._loop_task.cancel()
            self._loop_task.remove_done_callback(self._unexception)
