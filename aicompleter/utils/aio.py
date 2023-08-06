
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import Any, Coroutine, Optional

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

def thread_run(func):
    '''
    Run a function in a thread
    '''
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with ThreadPoolExecutor(1, "ThreadRun") as executor:
            return await asyncio.get_event_loop().run_in_executor(executor, func, *args, **kwargs)
    if 'return' in func.__annotations__:
        wrapper.__annotations__['return'] = Coroutine[None, None, func.__annotations__['return']]
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
    if srctext in ('enable', 'true', 'True', '1', 'yes', 'y', 't'):
        return True
    if srctext in ('disable', 'false', 'False', '0', 'no', 'n', 'f'):
        return False
    raise ValueError(f"Cannot convert {srctext} to bool")
