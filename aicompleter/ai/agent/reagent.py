'''
Refactor the agent class

This is a agent class which put more details to the Interface class.
'''
import asyncio
import contextlib
import copy
import json
from typing import Any, Callable, Coroutine, Iterable, Optional, Self
from ... import log
from ... import utils
from ...common import AsyncLifeTimeManager, JsonType
from ..ai import Conversation, ChatTransformer
from .. import ai as aiclass

class Agent(AsyncLifeTimeManager):
    '''
    Agent for the chatbot
    '''
    def __init__(self, ai: ChatTransformer, name:str = 'root', init_conversation: Optional[Conversation] = None, *, loop: Optional[asyncio.AbstractEventLoop] = None):
        super().__init__()
        self._ai = ai
        self._conversation = init_conversation if init_conversation is not None else Conversation()
        if loop == None:
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop
        self._on_response: Callable[[Self,aiclass.Message], Coroutine[None, None, None]] = lambda agent, message: None
        '''
        If the AI result is returned, the function will be called
        '''
        self._logger = log.getLogger('Agent', [name])
        self._parent:Optional[Self] = None
        self._name = name
        self._request_queue: asyncio.Queue[aiclass.Message | None] = asyncio.Queue()           # AI request queue, will send to the AI
        self._pre_request_time: float = 0.1                                             
        # The time between the requests, for example, the agent got a request at time 0,
        # and the next request(and all new requests) will be sent at time 0.1
        self._close_tasks.append(loop.create_task(self._agent_loop()))

        self._result = None

        self._subagents: dict[str, Self] = {}

    @property
    def result(self) -> Any:
        '''
        The result of the agent
        '''
        if not self.closed:
            raise RuntimeError('The agent is not closed')
        if isinstance(self._result, Exception):
            raise self._result
        else:
            return self._result

    @classmethod
    def create_subagent(cls, parent:Self, name:str) -> Self:
        '''
        Create a subagent
        '''
        def _get_parents_name(agent:Self):
            if agent._parent is None:
                return [agent._name]
            else:
                return [*_get_parents_name(agent._parent), agent._name]
        agent = cls(parent._ai, name, parent._conversation, loop=parent._loop)
        agent._parent = parent
        agent._logger.pop()
        agent._logger.push(_get_parents_name(agent))
        parent._subagents[name] = agent
        return agent
    
    def new_subagent(self, name:str) -> Self:
        '''
        Create a new subagent
        '''
        return self.create_subagent(self, name)
    
    async def _agent_loop(self):
        # The agent loop, will run in a coroutine, handle the AI result
        while not self.closed:
            request = await self._request_queue.get()
            requests = []
            if request is not None:
                requests.append(request)
                await asyncio.sleep(self._pre_request_time)
                while not self._request_queue.empty():
                    requests.append(self._request_queue.get_nowait())
            
            @contextlib.contextmanager
            def _append_conversation():
                # Append the conversation to the conversation list
                # The conversation will be removed when the context is exited
                before = copy.copy(self._conversation)
                self._conversation.messages.extend(requests)
                try:
                    yield self._conversation
                except Exception as e:
                    self._conversation = before
                    raise e
                
            with _append_conversation() as conversation:
                if self._logger.isEnabledFor(log.DEBUG):
                    reader: asyncio.StreamReader = asyncio.StreamReader()
                    logtask = self._loop.create_task(self._logger.debug_stream(reader))
                    last_content = ''
                    async for message in self._ai.generate(conversation):
                        new_content = message.content[len(last_content):]
                        last_content = message.content
                        if new_content:
                            reader.feed_data(new_content.encode())
                    await logtask
                    del reader, last_content, new_content, logtask
                else:
                    message = await self._ai.generate_message(conversation)
                # The message is generated
            
            self._conversation.messages.append(message)
            # parse the message
            await self._on_response(self, message)

    def set_result(self, result):
        '''
        Set the result of the agent
        '''
        if self.closed:
            raise RuntimeError('The agent is closed')
        self._result = result

    def __await__(self):
        yield from self._close_event.wait().__await__()
        return self.result
