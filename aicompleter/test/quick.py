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
        super().__init__(namespace=namespace, config=config)

    def on_init(self, func: Optional[Callable[..., Coroutine[None, None, None]]] = None):
        self.init = func
        return func

    def on_final(self, func: Optional[Callable[..., Coroutine[None, None, None]]] = None):
        self.final = func
        return func

    def on_sessioninit(self, func: Optional[Callable[..., Coroutine[None, None, None]]] = None):
        self.session_init = func
        return func

    def on_sessionfinal(self, func: Optional[Callable[..., Coroutine[None, None, None]]] = None):
        self.session_final = func
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
        return self.commands.register(*args, **kwargs)

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

null_handler = Handler()
'''
Null Handler instance

You can use it to test some commands,
this instance is for simple testing,
so it is not recommended to use it in production environment or for multi-instance testing

This handler instance will automatically setup the null_interface instance
'''
asyncio.run(null_handler.add_interface(null_interface))

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
        null_session = asyncio.run(null_handler.new_session(config))
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
    return asyncio.run(get_session().asend(*args, **kwargs))

def terminate():
    '''
    Terminate the session
    '''
    global null_session
    asyncio.run(get_session().close())
    null_session = None

