from __future__ import annotations
import asyncio
from typing import Any, Callable, Literal, TypeVar
import typing
import inspect

class defaultdict(dict):
    '''
    Dict that can automatically create new keys
    '''
    def __missing__(self, key):
        self[key] = defaultdict()
        return self[key]
