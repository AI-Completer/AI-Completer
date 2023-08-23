'''
Refactor the agent class

This is a agent class which put more details to the Interface class.
'''
import asyncio
import contextlib
import copy
from typing import Any, Callable, Coroutine, Iterable, Optional, Self
from ... import log
from ...common import AsyncLifeTimeManager
from ..ai import AuthorType, Conversation, ChatTransformer
from .. import ai as aiclass

class Agent(AsyncLifeTimeManager):
    '''
    Agent for the chatbot
    '''
    def __init__(self, ai: ChatTransformer, init_conversation: Optional[Conversation] = None, name:str = 'root',  *, loop: Optional[asyncio.AbstractEventLoop] = None):
        super().__init__()
        self._ai = ai
        self.conversation = init_conversation if init_conversation is not None else Conversation()
        if loop == None:
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop
        self._on_response: Callable[[Self,aiclass.Message], Coroutine[None, None, None]] = lambda agent, message: self._loop.create_future()
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

        task = self._loop.create_task(self._agent_loop())

        self._result = None
        def _done(_task: asyncio.Task):
            if _task.exception():
                self._result = _task.exception()
            self._close_event.set()
        task.add_done_callback(_done)

        self._subagents: dict[str, Self] = {}

    def on_response(self, func: Callable[[Self,aiclass.Message], Coroutine[None, None, None]]):
        '''
        Set the on_response function
        '''
        self._on_response = func

    @property
    def config(self):
        return self._ai.config
    
    @config.setter
    def config(self, value):
        self._ai.config = value

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
        agent = cls(parent._ai, parent.conversation, name, loop=parent._loop)
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
                    to_add = self._request_queue.get_nowait()
                    if to_add != None:
                        requests.append(to_add)
            for request in requests:
                self._logger.debug('Got request: %s', repr(request))

            @contextlib.contextmanager
            def _append_conversation():
                # Append the conversation to the conversation list
                # The conversation will be removed when the context is exited
                before = copy.copy(self.conversation)
                self.conversation.messages.extend(requests)
                try:
                    yield self.conversation
                except Exception as e:
                    self.conversation = before
                    raise e
                
            with _append_conversation() as conversation:
                if self._logger.isEnabledFor(log.DEBUG):
                    reader: asyncio.StreamReader = asyncio.StreamReader()
                    logtask = self._loop.create_task(self._logger.debug_stream(reader))
                    last_content = ''
                    reader.feed_data('AI response: '.encode())
                    try:
                        async for message in self._ai.generate(conversation):
                            new_content = message.content[len(last_content):]
                            last_content = message.content
                            if new_content:
                                reader.feed_data(new_content.encode())
                    except Exception as e:
                        reader.feed_eof()
                        await logtask
                        self._logger.exception('Error when generating message: %s', e)
                        raise e
                    reader.feed_eof()
                    await logtask
                    del reader, last_content, new_content, logtask
                else:
                    message = await self._ai.generate_message(conversation)
                # The message is generated
            
            self.conversation.messages.append(message)
            # parse the message
            await self._on_response(self, message)

    def set_result(self, result):
        '''
        Set the result of the agent
        '''
        if self.closed:
            raise RuntimeError('The agent is closed')
        self._result = result

    def append_message(self, message: aiclass.Message):
        '''
        Append a message to the conversation
        '''
        if self.closed:
            raise RuntimeError('The agent is closed')
        self._request_queue.put_nowait(message)

    def append_word(self, word: str, user:Optional[str] = None, data:Optional[dict] = None):
        '''
        Append a user message to the conversation
        '''
        if self.closed:
            raise RuntimeError('The agent is closed')
        self._request_queue.put_nowait(aiclass.Message(word, role=AuthorType.USER, user=user, data=data))

    def append_system(self, prompt:str, data:Optional[dict] = None):
        self.append_message(aiclass.Message(prompt, role=AuthorType.SYSTEM, data=data))

    def trigger(self):
        '''
        Trigger the agent, without any message
        '''
        if self.closed:
            raise RuntimeError('The agent is closed')
        self._request_queue.put_nowait(None)

    def __await__(self):
        yield from self._close_event.wait().__await__()
        return self.result
