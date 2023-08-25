import asyncio
import copy
import json
import traceback
from typing import Any, Callable, Coroutine, NoReturn, Optional, Self, Union, overload
from ... import *
from ... import events
from .. import ChatTransformer

class Agent(common.AsyncLifeTimeManager):
    '''
    AI Agent
    '''
    def __init__(self, chatai: ChatTransformer, init_prompt:Optional[str] = None, user:Optional[str] = None, loop:Optional[asyncio.AbstractEventLoop] = None):
        super().__init__()
        self.ai = chatai
        self._init_prompt = init_prompt
        self._loop = loop = loop or asyncio.get_event_loop()
        
        self.conversation = self.ai.new_conversation(user,init_prompt=init_prompt)
        '''The conversation of the agent'''
        self.on_call: Callable[[str, Any], Coroutine[Any, None, None]] = lambda cmd, param: self._loop.create_task()
        '''Event when a command is called'''
        self.on_subagent: Callable[[str, Any], None | Coroutine[None, None, None]] = lambda name, word: self.new_subagent(name, word)
        '''Event when a subagent is created'''
        self.on_exception: events.Event = events.Event(callbacks=[lambda e: print(traceback.format_exc())])
        '''Event when an exception is raised'''
        self.enable_ask = True
        '''Enable the ask command'''

        self._result_queue: asyncio.Queue[interface.Result] = asyncio.Queue()
        self._request_queue: asyncio.Queue[ai.Message | None] = asyncio.Queue()
        self._handle_task = loop.create_task(self._handle_result())
        self._loop_task = loop.create_task(self._handle_loop())
        self._result = ...

        self._subagents:dict[str, Self] = {}

        self._parent:Optional[Agent] = None
        self._parent_name = None

        def _getstruct(value:Self):
            if value._parent:
                return [*_getstruct(value._parent), value._parent_name]
            return [value.ai.name]
        self.logger = log.getLogger('Agent', _getstruct(self))

        self._handle_task.add_done_callback(self._unexception)
        self._loop_task.add_done_callback(self._unexception)

        self._last_result = None

    def _unexception(self,x:asyncio.Future):
        try:
            x.result()
        except asyncio.CancelledError as e:
            pass
        except Exception as e:
            self._loop.create_task(self.on_exception(e))
    
    @property
    def result(self) -> Any:
        '''
        The result of the agent
        '''
        if not self.closed:
            raise error.AI_OnRun('The agent is not stopped yet')
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result

    def new_subagent(self, name:str, init_words: str,init_prompt:Optional[str] = None, ai: Optional[ChatTransformer] = None , user:Optional[str] = None) -> Self:
        '''
        Create a subagent
        '''
        self._subagents[name] = Agent(ai or self.ai, init_prompt or self._init_prompt, user, self._loop)
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
        to_add = ai.Message(
            content = json.dumps(value, ensure_ascii = False),
            role=role,
        )
        if role == 'user':
            to_add.user = self.conversation.user
        self._request_queue.put_nowait(to_add)

    def _parse(self, raw:str):
        '''
        Parse the commands from AI
        '''

        def _check_parse(value:str) -> bool:
            try:
                json.loads(value)['commands']
                return True
            except Exception:
                return False

        content_list = []
        command_raw = None
        if _check_parse(raw):
            command_raw = raw
        else:
            if raw[0] == '{' and raw[-1] == '}':
                raise ValueError('Commands parse error, please check your json format and retry, the format: {"commands":[{...}]}')

            for line in raw.splitlines():
                if _check_parse(line):
                    command_raw = line
                else:
                    content_list.append(line)
                    if command_raw is not None:
                        raise ValueError('Json format is not allowed before the content')

        json_dat = {"commands":[]}
        if content_list:
            json_dat['commands'].append({"cmd":"ask", "param": {"content": '\n'.join(content_list)}})
        if command_raw is not None:
            json_dat['commands'].extend(json.loads(command_raw)['commands'])

        if len(json_dat['commands']) == 0:
            raise ValueError('No commands found')

        self.conversation.messages[-1].content = json.dumps(json_dat, ensure_ascii = False)

        for cmd in json_dat['commands']:
            if not isinstance(cmd, dict):
                raise ValueError('Invalid command format')
            if not isinstance(cmd.get('cmd', None), str):
                raise ValueError('command name not found')
            if not isinstance(cmd.get('param', None), (dict,str)):
                raise ValueError('command parameters not found')
        
        return json_dat

    async def _handle_loop(self):
        '''
        The loop for the agent
        '''
        from ... import ai
        stop_flag = False
        exception = None
        try:
            while not stop_flag:
                await asyncio.sleep(0.1)
                # Get all the requests

                request:ai.Message = await self._request_queue.get()
                # Wait for other command output
                await asyncio.sleep(0.1)

                requests = [request]
                while not self._request_queue.empty():
                    requests.append(self._request_queue.get_nowait())

                # Remove None
                requests = [i for i in requests if i is not None]
                if len(requests) == 0:
                    self.logger.debug('Empty request')
                else:
                    self.logger.debug(f'Get requests: {requests}')

                _new_conversation = copy.deepcopy(self.conversation)
                for request in requests:
                    _new_conversation.messages.append(request)
                raw = await self.ai.generate_text(conversation=_new_conversation)
                # Success
                _new_conversation.messages.append(ai.Message(
                    content = raw,
                    role = 'assistant',
                ))
                self.conversation = _new_conversation

                self.logger.debug(f'AI response: {raw}')
                if raw == '':
                    # Self call ask command, do not input anything
                    raw = '{"commands":[{"cmd":"ask","param":{"content":""}}]}'

                # try to replace the variables
                raw = raw.replace('$last_result', str(self._last_result) or '')

                try:
                    json_dat = self._parse(raw)
                except ValueError as e:
                    # no wait to tell AI
                    self.logger.error(f'Value Error: {str(e)}')
                    self._request({
                        'type':'error',
                        'value':str(e),
                    })
                    continue

                # Refactor the last message
                self.conversation.messages[-1] = ai.Message(
                    content = json.dumps(json_dat, ensure_ascii = False),
                    role = 'assistant',
                )
                
                json_dat = json_dat['commands']
                if len(json_dat) == 0:
                    continue

                # Execute the commands
                for cmd in json_dat:
                    if cmd['cmd'] == 'stop':
                        stop_flag = True
                        self._result = cmd.pop('param', None)
                        if self._parent:
                            self._parent._subagents.pop(self._parent_name)
                        continue
                    if cmd['cmd'] == 'agent':
                        # Create a subagent
                        if not all(i in cmd['param'] for i in ('name', 'task')):
                            self._request({
                                'type':'error',
                                'value':f"Paremeters 'name' and 'word' are required"
                            })
                        if cmd['param']['name'] in self._subagents:
                            self._subagents[cmd['param']['name']].ask(cmd['param']['task'])
                            continue
                        ret = self.on_subagent(cmd['param']['name'], cmd['param']['task'])
                        if asyncio.iscoroutine(ret):
                            await ret
                        continue
                    if cmd['cmd'] == 'ask':
                        if not self.enable_ask:
                            self._request({
                                'type':'error',
                                'value':f"Ask command is not allowed, if possible, use 'stop' instead"
                            })
                            continue
                        # This command will be hooked if the agent is a subagent
                        if self._parent:
                            self._parent._subagent_ask(self._parent_name, cmd['param'])
                            await asyncio.sleep(0.1)
                            continue
                    
                    def wrap_context():
                        curcmd = cmd
                        def when_result(x: asyncio.Future):
                            try:
                                ret = x.result()
                            except asyncio.CancelledError:
                                return
                            except Exception as e:
                                # Unpack Exception, remove the interface & session (to reduce the lenght of the message)
                                if isinstance(e, error.BaseException):
                                    e.kwargs.pop('interface', None)
                                    e.kwargs.pop('handler', None)
                                    e.kwargs.pop('session', None)
                                    e.parent = None
                                self._result_queue.put_nowait(interface.Result(curcmd['cmd'], False, str(e)))
                                self.logger.error(f'Exception when executing command {curcmd["cmd"]}: {e}')
                            else:
                                self._result_queue.put_nowait(interface.Result(curcmd['cmd'], True, ret))
                                self.logger.info(f'Command {curcmd["cmd"]} executed successfully, Result: {ret}')
                        self._loop.create_task(self.on_call(curcmd['cmd'], curcmd['param'])).add_done_callback(when_result)

                    wrap_context()
            
        except asyncio.CancelledError as e:
            exception = e
        except Exception as e:
            exception = e
            self.logger.error(f'Exception: {e}')
            if self.logger.isEnabledFor(log.DEBUG):
                traceback.print_exc()
        finally:
            # The loop is done
            self.logger.debug('The agent is stopped')
            self._loop.create_task(self.close())
            if exception is not None:
                if isinstance(exception, asyncio.CancelledError):
                    raise exception
                else:
                    self._result = exception
            
        self.logger.debug('The loop is done')

    async def _handle_result(self) -> Coroutine[None, None, NoReturn]:
        while True:
            result = await self._result_queue.get()
            if result.cmd == 'ask':
                # Excpetion
                self.ask(result.ret)
                continue

            self._last_result = result.ret
            self._request({
                'type':'command-result',
                'success': result.success,
                'result': result.ret,
            })

    def ask(self, value:str):
        '''
        Ask the agent to execute a command
        '''
        from ... import ai
        self._request_queue.put_nowait(ai.Message(
            content = value,
            role = 'user',
            user = self.conversation.user,
        ))

    def trigger(self):
        '''
        Do nothing, just trigger the agent to run
        '''
        self.logger.debug('Triggered')
        self._request_queue.put_nowait(None)

    def _subagent_ask(self, name:str, value:str):
        '''
        Ask the agent to execute a command
        '''
        self.logger.debug(f'The subagent[{name}] ask: {value}')
        self._request({
            'type':'ask-from-subagent',
            'name': name,
            'value': value,
        })

    async def close(self):
        '''
        Close the agent
        '''
        if self.closed:
            return
        if self._handle_task:
            self._handle_task.cancel()
            self._handle_task.remove_done_callback(self._unexception)
            try:
                await self._handle_task
            except asyncio.CancelledError:
                pass
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task.remove_done_callback(self._unexception)
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        self._handle_task = None
        self._loop_task = None
        self.logger.debug('The agent is closed')
        await super().close()

    def wait(self):
        '''
        Wait until the agent is stopped
        '''
        return self.wait_close()

    def __del__(self):
        if not self.closed:
            self.close()
