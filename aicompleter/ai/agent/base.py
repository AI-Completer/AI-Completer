import asyncio
import json
import traceback
from typing import Any, Callable, Coroutine, Optional, Self, overload
from ... import *
from ... import events
from .. import ChatTransformer

class Agent:
    '''
    AI Agent
    '''
    def __init__(self, chatai: ChatTransformer, init_prompt:str, user:Optional[str] = None):
        self.ai = chatai
        self._init_prompt = init_prompt
        
        self.conversation = self.ai.new_conversation(user,init_prompt=init_prompt)
        '''The conversation of the agent'''
        self.on_call: Callable[[str, Any], Coroutine[Any, None, None]] = lambda cmd, param: asyncio.create_task()
        '''Event when a command is called'''
        self.on_subagent: Callable[[str, Any], None | Coroutine[None, None, None]] = lambda name, word: self.new_subagent(name, word)
        '''Event when a subagent is created'''
        self.on_exception: events.Event = events.Event(callbacks=[lambda e: print(traceback.format_exc())])
        '''Event when an exception is raised'''
        self.enable_ask = True
        '''Enable the ask command'''

        self._result_queue: asyncio.Queue[interface.Result] = asyncio.Queue()
        self._request_queue: asyncio.Queue[ai.Message] = asyncio.Queue()
        self._handle_task = asyncio.get_event_loop().create_task(self._handle_result())
        self._loop_task = asyncio.get_event_loop().create_task(self._loop())
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

    async def _unexception(self,x:asyncio.Future):
        try:
            return x.result()
        except Exception as e:
            await self.on_exception(e)
            return e

    @property
    def stopped(self) -> bool:
        '''
        Whether the agent is stopped
        '''
        return self._result != Ellipsis
    
    @property
    def result(self) -> Any:
        '''
        The result of the agent
        '''
        if self._result != Ellipsis:
            raise RuntimeError('The agent is not stopped yet')
        return self._result

    def new_subagent(self, name:str, init_words: str,init_prompt:Optional[str] = None, ai: Optional[ChatTransformer] = None , user:Optional[str] = None) -> Self:
        '''
        Create a subagent
        '''
        self._subagents[name] = Agent(ai or self.ai, init_prompt or self._init_prompt, user)
        self._subagents[name].on_call = self.on_call
        self._subagents[name]._parent = self
        self._subagents[name]._parent_name = name
        self._subagents[name].ask(init_words)
        self.logger.debug(f'Create subagent {name}')
        return self._subagents[name]

    def _request(self, value:dict):
        '''
        Ask the agent to execute a command
        '''
        from ... import ai
        self._request_queue.put_nowait(ai.Message(
            content = json.dumps(value, ensure_ascii = False),
            user=self.conversation.user,
            role='user',
        ))

    def _parse(self, raw:str):
        '''
        Parse the commands from AI
        '''

        # Check this format : {"type":"ask", "message":"<message>"}
        try:
            json_dat = json.loads(raw)
            if not isinstance(json_dat, dict):
                raise ValueError('Invalid json format')
            if not isinstance(json_dat.get('type', None), str):
                raise ValueError('type not found')
            if json_dat['type'] == 'ask' and 'message' in json_dat:
                raw = json_dat['message']
        except Exception:
            pass


        def _check_parse(value:str) -> bool:
            try:
                json.loads(value)['commands']
                return True
            except Exception:
                return False

        content_list = []
        command_raw = None
        for line in raw.splitlines():
            if _check_parse(line):
                command_raw = line
            else:
                content_list.append(line)
                if command_raw is not None:
                    raise ValueError('Json format is not allowed before the content')

        json_dat = {"commands":[]}
        if content_list:
            json_dat['commands'].append({"cmd":"ask", "param": '\n'.join(content_list)})
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

    async def _loop(self):
        '''
        The loop for the agent
        '''
        from ... import ai
        stop_flag = False
        try:
            while not stop_flag:
                await asyncio.sleep(0.1)
                # Get all the requests

                requests:list[ai.Message] = [await self._request_queue.get()]
                while not self._request_queue.empty():
                    requests.append(self._request_queue.get_nowait())

                self.logger.debug(f'Get requests: {requests}')

                def _try_parse(x):
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

                raw = await self.ai.ask_once(
                    history = self.conversation,
                    message = ai.Message(
                        content = raw_content,
                        role = 'user',
                        user = self.conversation.user,
                    ),
                )
                self.logger.debug(f'AI response: {raw}')
                if raw == '':
                    # Self call ask command, do not input anything
                    raw = '{"commands":[{"cmd":"ask","param":""}]}'

                try:
                    json_dat = self._parse(raw)
                except ValueError as e:
                    # no wait to tell AI
                    self.logger.error(f'Invalid json format: {raw}')
                    self._request({
                        'type':'error',
                        'value':str(e),
                    })
                    continue
                
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
                                'value':f"Ask command is not allowed"
                            })
                            continue
                        # This command will be hooked if the agent is a subagent
                        if self._parent:
                            self._parent._subagent_ask(self._parent_name, cmd['param'])
                            await asyncio.sleep(0.1)
                            continue

                    def when_result(x: asyncio.Future):
                        try:
                            ret = x.result()
                        except asyncio.CancelledError:
                            return
                        except Exception as e:
                            self._result_queue.put_nowait(interface.Result(cmd['cmd'], False, str(e)))
                            self.logger.error(f'Exception when executing command {cmd["cmd"]}: {e}')
                        else:
                            self._result_queue.put_nowait(interface.Result(cmd['cmd'], True, ret))
                            self.logger.info(f'Command {cmd["cmd"]} executed successfully, Result: {ret}')

                    asyncio.get_event_loop().create_task(self.on_call(cmd['cmd'], cmd['param'])).add_done_callback(when_result)
        except asyncio.CancelledError as e:
            # The loop is done
            self._handle_task.remove_done_callback(self._unexception)
            self._loop_task.remove_done_callback(self._unexception)
            self._handle_task.cancel()
            self._handle_task = None
            self._loop_task = None
            self.logger.debug('The agent is stopped')
            raise e

        # The loop is done
        self._handle_task.remove_done_callback(self._unexception)
        self._loop_task.remove_done_callback(self._unexception)
        self._handle_task.cancel()
        self._handle_task = None
        self._loop_task = None
        self.logger.debug('The agent is stopped')
        # Will end itself

    async def _handle_result(self):
        while True:
            result = await self._result_queue.get()

            if result.cmd == 'ask':
                # Excpetion
                self.ask(result.ret)
                continue

            self._request({
                'type':'command-result',
                'success': result.success,
                'command-result': result.ret,
            })

    def ask(self, value:str):
        '''
        Ask the agent to execute a command
        '''
        self.logger.debug(f'The upper layer ask: {value}')
        self._request({
            'type':'ask-from-user',
            'value':value,
        })

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

    def __del__(self):
        if self._handle_task:
            self._handle_task.cancel()
            self._handle_task.remove_done_callback(self._unexception)
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task.remove_done_callback(self._unexception)
