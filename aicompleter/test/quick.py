'''
Some simple operations for testing

In general, you can use this module to test some commands, or to test some functions that require an interface.
You should not use this module in production environment.

Example:
--------
::
    >>> from aicompleter.test.quick import *
    >>> @null_interface.on_init
    ... async def init():
    ...     print('init')
    >>> @null_interface.register('test', 'test command')
    ... async def test():
    ...     print('test')
    >>> call('test')    # This operation will automatically create a session
    init
    test
::
'''
from abc import ABCMeta
import asyncio
from typing import Any, Callable, Coroutine, Iterable, Optional, overload

from aicompleter.interface.command import CommandAuthority
from .. import *

class NullInterfaceMeta(common.SingletonMeta, ABCMeta):
    '''
    Null Interface Meta

    Just resolve the conflict between SingletonMeta and ABCMeta
    '''
    pass

class NullInterface(common.Singleton,Interface, metaclass=NullInterfaceMeta):
    '''
    Null Interface, just for testing

    This interface is a singleton, and it is used for testing.
    '''
    def __init__(self, namespace:Optional[str] = None, config:Config = Config()):
        namespace = namespace or 'null'
        super().__init__(namespace=namespace, config=config, user=User(
            name="null",
        ))
        self._init = None
        self._final = None
        self._session_init = None
        self._session_final = None

    async def init(self, in_handler:Handler):
        if self._init:
            params = utils.appliable_parameters(self._init, {
                'in_handler': in_handler,
                'handler': in_handler,
            })
            ret = self._init(**params)
            if asyncio.iscoroutine(ret):
                await ret

    async def final(self, in_handler:Handler):
        if self._final:
            param = utils.appliable_parameters(self._final,{
                'in_handler': in_handler,
                'handler': in_handler,
            })
            ret = self._final(**param)
            if asyncio.iscoroutine(ret):
                await ret
            
    async def session_init(self, session:Session, data:EnhancedDict, config: Config):
        if self._session_init:
            param = utils.appliable_parameters(self._session_init,{
                'session': session,
                'data': data,
                'config': config,
            })
            ret = self._session_init(**param)
            if asyncio.iscoroutine(ret):
                await ret

    async def session_final(self, session:Session, data:EnhancedDict, config: Config):
        if self._session_final:
            param = utils.appliable_parameters(self._session_final,{
                'session': session,
                'data': data,
                'config': config,
            })
            ret = self._session_final(**param)
            if asyncio.iscoroutine(ret):
                await ret

    def setConfigFactory(self, factory:Callable[..., Any]):
        '''
        Set the config factory of the interface
        '''
        self.configFactory = factory

    def setDataFactory(self, factory:Callable[..., Any]):
        '''
        Set the data factory of the interface
        '''
        self.dataFactory = factory
        if isinstance(self.namespace.data, DataModel):
            self.namespace.data = factory(self.namespace.data.__wrapped__)
        else:
            self.namespace.data = factory(self.namespace.data)

    def on_init(self, func: Optional[Callable[..., Coroutine[None, None, None]]] = None):
        self._init = func
        return func

    def on_final(self, func: Optional[Callable[..., Coroutine[None, None, None]]] = None):
        self._final = func
        return func

    def on_sessioninit(self, func: Optional[Callable[..., Coroutine[None, None, None]]] = None):
        self._session_init = func
        return func

    def on_sessionfinal(self, func: Optional[Callable[..., Coroutine[None, None, None]]] = None):
        self._session_final = func
        return func
    
    def run(self, cmdname:str, *args:Any, loop:Optional[asyncio.AbstractEventLoop] = None, **kwargs:Any):
        '''
        run a command
        '''
        cmd = self.commands.get(cmdname)
        if cmd is None:
            raise error.NotFound('Command %s not found' % cmdname)
        if cmd.callback is None:
            raise AssertionError('Command %s has no callback, and in "run" method, no session is generated.' % cmdname)
        ret = cmd.callback(*args, **kwargs)
        if asyncio.iscoroutine(ret):
            if loop is None:
                ret = asyncio.run(ret)
            else:
                ret = loop.run_until_complete(ret)
        return ret

    @overload
    def register(self, command:Command):
        ...

    @overload
    def register(self, 
                 cmd:str, 
                 description:str="", 
                 *, 
                 alias:set[str]=set(), 
                 format:Optional[CommandParamStruct | dict[str, Any]]=None, 
                 callable_groups:set[str]=set(), 
                 overrideable:bool=False, 
                 extra:dict={}, 
                 expose:bool=True, 
                 authority:CommandAuthority=CommandAuthority(), 
                 to_return:bool=True,
                 **kwargs):
        ...

    def register(self, *args, **kwargs):
        kwargs['in_interface'] = self
        return self.commands.register(*args, **kwargs)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

null_interface = NullInterface()
'''
Null Interface instance

You can use it to test some commands,
this instance is for simple testing, 
so it is not recommended to use it in production environment or for multi-instance testing

Example:
--------
::
    >>> from aicompleter.test.quick import null_interface
    >>> @null_interface.register('test', 'test command')
    ... async def test():
    ...     print('test')
    >>> null_interface.run('test')
'''

null_handler:Optional[Handler] = None
'''
Null Handler instance

You can use it to test some commands,
this instance is for simple testing,
so it is not recommended to use it in production environment or for multi-instance testing

This handler instance will automatically setup the null_interface instance
'''
def get_handler():
    '''
    Get a handler

    if the handler is not created, it will create a new handler
    '''
    global null_handler
    if null_handler == None:
        null_handler = Handler(loop=loop)
        loop.run_until_complete(null_handler.add_interface(null_interface))
    return null_handler

null_session:Optional[Session] = None
'''
Null Session instance
'''

def get_session(config:Config = Config()) -> Session:
    '''
    Get a session

    if the session is not created, it will create a new session
    '''
    global null_session
    if null_session is None:
        null_session = loop.run_until_complete(get_handler().new_session(config))
    return null_session

@overload
def call(message:Message):
    ...

@overload
def call(cmd:str, 
    content:MultiContent = MultiContent(),
    *,
    data:EnhancedDict = EnhancedDict(), 
    last_message: Optional[Message] = None,
    src_interface:Optional[Interface] = None,
    dest_interface:Optional[Interface] = None,):
    ...

def call(*args, **kwargs):
    '''
    Call a command
    '''
    return loop.run_until_complete(get_session().asend(*args, **kwargs))

def terminate():
    '''
    Terminate the session
    '''
    global null_session
    loop.run_until_complete(get_session().close())
    null_session = None

