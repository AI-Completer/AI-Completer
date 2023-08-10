
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import Any, Callable, Coroutine, Generator, Optional, TypeVar
import typing

_T = TypeVar('_T')
_on_reading:asyncio.Lock = asyncio.Lock()
'''
Global asyncio lock for console input
'''

async def ainput(prompt: str = "") -> str:
    '''
    Async input
    '''
    async with _on_reading:
        with ThreadPoolExecutor(1, "AsyncInput") as executor:
            return (await asyncio.get_event_loop().run_in_executor(executor, input, prompt)).rstrip()

async def aprint(string: str) -> None:
    '''
    Async print
    '''
    async with _on_reading:
        print(string)

def thread_run(func:Callable[..., _T], *args, **kwargs) -> Callable[..., asyncio.Future[_T]] | typing.Awaitable[_T]:
    '''
    Run a function in a thread, and return a coroutine

    Examples
    --------
    ::
        >>> import asyncio
        >>> asyncio.run(thread_run(lambda x: x + 1, 1))
        2
        >>> asyncio.run(thread_run(lambda x, y: x + y)(1, 2))
        3
        >>> @thread_run
        ... def add(x, y):
        ...     return x + y
        >>> asyncio.run(add(1, 2))
        3
    '''
    if len(args) or len(kwargs):
        return thread_run(functools.partial(func, *args, **kwargs))
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> asyncio.Future[_T]:
        with ThreadPoolExecutor(1, "ThreadRun") as executor:
            return asyncio.get_event_loop().run_in_executor(executor, func, *args, **kwargs)
    if 'return' in func.__annotations__:
        wrapper.__annotations__['return'] = Coroutine[None, None, func.__annotations__['return']]
    wrapper.__await__ = lambda: wrapper().__await__()
    return wrapper

def is_enable(srctext:bool | str, default:bool = True) -> bool:
    '''
    Convert a string to bool, as possible
    '''
    if isinstance(srctext, bool):
        return srctext
    srctext = srctext.strip()
    if srctext == '':
        return default
    if srctext in ('enable', 'true', 'True', '1', 'yes', 'y', 't', 'Yes', 'Y', 'T', 'On', 'on'):
        return True
    if srctext in ('disable', 'false', 'False', '0', 'no', 'n', 'f', 'No', 'N', 'F', 'Off', 'off'):
        return False
    raise ValueError(f"Cannot convert {srctext} to bool")
