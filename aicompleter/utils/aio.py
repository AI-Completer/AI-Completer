
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import Any, AsyncGenerator, Callable, Coroutine, Generator, Optional, TypeVar
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

async def aiterfunc(func: Callable[..., Coroutine], sentinel: Any = None) -> AsyncGenerator[Any, None]:
    '''
    Convert a function to a async iterator

    Examples
    --------
    ::
        >>> import asyncio
        >>> value = 0
        >>> async def func():
        ...     global value
        ...     await asyncio.sleep(1)
        ...     value += 1
        ...     return value
        >>> async def main():
        ...     async for i in aiterfunc(func, 3):
        ...         print(i)
        >>> asyncio.run(main())
        1
        2
    '''
    while True:
        ret = await func()
        if ret == sentinel:
            break
        yield ret

def retry(func:Optional[Callable[..., _T]], /, max_time:int = 0, on_failed:Optional[Callable[[int], _T]] = None):
    '''
    Retry a function

    Parameters
    ----------
    func : Callable[..., _T]
        The function to retry
    max_time : int, optional
        The max retry times, by default 0

    Returns
    -------
    Callable[..., _T]
        The wrapped function
    '''
    if func is None:
        return functools.partial(retry, max_time=max_time)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for _ in range(max_time + 1):
            try:
                return func(*args, **kwargs)
            except BaseException as e:
                if on_failed is not None:
                    on_failed(_)
                if _ == max_time:
                    raise e
        raise
    return wrapper

def retry_async(func:Optional[Callable[..., Coroutine]], /, max_time:int = 0, on_failed:Optional[Callable[..., Coroutine|None]] = None):
    '''
    Retry a async function

    Parameters
    ----------
    func : Callable[..., Coroutine]
        The function to retry
    max_time : int, optional
        The max retry times, by default 0

    Returns
    -------
    Callable[..., Coroutine|None]
        The wrapped function
    '''
    if func is None:
        return functools.partial(retry_async, max_time=max_time)
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        for _ in range(max_time + 1):
            try:
                return await func(*args, **kwargs)
            except BaseException as e:
                if on_failed is not None:
                    ret = on_failed(_)
                    if asyncio.iscoroutine(ret):
                        await ret
                if _ == max_time:
                    raise e
        raise
    return wrapper
