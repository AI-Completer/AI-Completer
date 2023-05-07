'''
Utils for autodone
'''
from __future__ import annotations
import sys
import asyncio

class defaultdict(dict):
    '''
    Dict that can automatically create new keys
    '''
    def __missing__(self, key):
        self[key] = defaultdict()
        return self[key]

_on_reading:asyncio.Lock = asyncio.Lock()
'''
Global asyncio lock for console input
'''

async def ainput(string: str = "") -> str:
    '''
    Async input
    '''
    await _on_reading.acquire()
    await asyncio.get_event_loop().run_in_executor(
            None, lambda s=string: sys.stdout.write(s))
    ret = await asyncio.get_event_loop().run_in_executor(
            None, sys.stdin.readline)
    _on_reading.release()
    return ret

async def aprint(string: str) -> None:
    '''
    Async print
    '''
    await _on_reading.acquire()
    await asyncio.get_event_loop().run_in_executor(
            None, lambda s=string: sys.stdout.write(s))
    _on_reading.release()
