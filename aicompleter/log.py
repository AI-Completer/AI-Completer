'''
Custom logging module
'''

import asyncio
import logging
import os
import sys
from collections.abc import Mapping
from types import TracebackType
from typing import Iterable, Optional, TypeAlias
from . import config

import colorama

_on_reading:asyncio.Lock = asyncio.Lock()

CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
ERROR = logging.ERROR
WARNING = logging.WARNING
WARN = logging.WARN
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET

_SysExcInfoType: TypeAlias = tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None]
_ExcInfoType: TypeAlias = None | bool | _SysExcInfoType | BaseException
_ArgsType: TypeAlias = tuple[object, ...] | Mapping[str, object]

colorama.init()

class Formatter(logging.Formatter):
    '''
    Custom formatter
    eg. Formatter(['interface','console'])
    '''
    def __init__(self, substruct:Iterable[str] = [], colormap:Optional[dict[int,str]] = None):
        self.substruct = substruct
        self.colormap = {
            logging.DEBUG: colorama.Fore.BLUE,
            logging.INFO: colorama.Fore.GREEN,
            logging.WARNING: colorama.Fore.YELLOW,
            logging.ERROR: colorama.Fore.RED,
            logging.CRITICAL: colorama.Fore.RED + colorama.Style.BRIGHT
        }
        if colormap:
            self.colormap.update(colormap)
        super().__init__("{asctime}", None, "{")

    def getColor(self, levelno:int) -> str:
        '''
        Get color from colormap
        '''
        return self.colormap[int(levelno / 10) * 10]

    def format(self, record:logging.LogRecord) -> str:
        '''
        Format the record
        '''
        nrecord = record
        nrecord.message = record.getMessage()
        nrecord.asctime = colorama.Fore.BLACK + colorama.Style.DIM + self.formatTime(record, self.datefmt) + colorama.Fore.RESET + colorama.Style.RESET_ALL
        nrecord.levelname = self.getColor(record.levelno) + record.levelname + colorama.Fore.RESET
        nrecord.name = colorama.Fore.WHITE + colorama.Style.DIM + record.name + colorama.Fore.RESET + colorama.Style.RESET_ALL
        nrecord.message = colorama.Fore.WHITE + record.getMessage() + colorama.Fore.RESET
        nrecord.__dict__['substruct'] = "".join([
            f"[{colorama.Fore.WHITE + colorama.Style.DIM + sub + colorama.Fore.RESET + colorama.Style.RESET_ALL}]" 
                for sub in self.substruct
        ])

        self._fmt = \
            "{asctime} - " + \
            "{levelname:>6}" + \
            " [{name}]" + "{substruct} {message}"

        return self._fmt.format(**nrecord.__dict__)

ConsoleHandler = logging.StreamHandler

class Logger(logging.Logger):
    '''
    Custom logger
    '''
    def __init__(self, name:str, level:int = logging.NOTSET):
        super().__init__(name, level)
        self._stack = []

    def _update_formatter(self) -> None:
        '''
        Update formatter
        '''
        for handler in self.handlers:
            if isinstance(handler.formatter, Formatter):
                handler.formatter.substruct = self._stack

    def push(self, name:str) -> None:
        '''
        Push a name to stack
        '''
        self._stack.append(str(name))
        self._update_formatter()

    def pop(self) -> str:
        '''
        Pop a name from stack
        '''
        ret = self._stack.pop()
        self._update_formatter()
        return ret
    
    async def _log_async(self, level: int, msg: object, args: _ArgsType = (), exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1) -> None:
        async with _on_reading:
            return super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
    
    # Conflicts with the default input and output system (utlis.aio.ainput, utils.aio.aprint, print, input)

    # def _log(self, level: int, msg: object, args: _ArgsType, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1) -> None:
    #     # Get the asyncio loop (if any) for this thread
    #     loop = asyncio._get_running_loop()
    #     if loop is None:
    #         return super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
    #     else:
    #         return loop.create_task(self._log_async(level, msg, args, exc_info, extra, stack_info, stacklevel))
    
    async def log_stream(self, level: int, msg: asyncio.StreamReader, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1) -> None:
        if not self.isEnabledFor(level):
            return
        async with _on_reading:
            # Record the console cursor
            print("\033[s",end="")
            # Get console formater
            formatter = [i.formatter for i in self.handlers if isinstance(i, ConsoleHandler)][0]
            # Stream the log
            output = ""
            srcfile = os.path.normcase(__file__)
            while True:
                output += await msg.read(1)
                # Move the cursor to the recorded position
                print("\033[u",end="",flush=True)
                if output == "":
                    break
                # Print the log
                # The code is copied from logging.Logger._log
                sinfo = None
                if srcfile:
                    #IronPython doesn't track Python frames, so findCaller raises an
                    #exception on some versions of IronPython. We trap it here so that
                    #IronPython can use logging.
                    try:
                        fn, lno, func, sinfo = self.findCaller(stack_info, stacklevel)
                    except ValueError: # pragma: no cover
                        fn, lno, func = "(unknown file)", 0, "(unknown function)"
                else: # pragma: no cover
                    fn, lno, func = "(unknown file)", 0, "(unknown function)"
                if exc_info:
                    if isinstance(exc_info, BaseException):
                        exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
                    elif not isinstance(exc_info, tuple):
                        exc_info = sys.exc_info()
                record = self.makeRecord(self.name, level, fn, lno, output, args,
                                        exc_info, func, extra, sinfo)
                print(formatter.format(record), end="", flush=True)
            
            # Use the original log function to log the output
            self._log(level, output, args, exc_info, extra, stack_info, stacklevel)

    async def typewriter_log(self, level: int, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1) -> None:
        class Typewriter(asyncio.StreamReader):
            def __init__(self, msg:str):
                self.msg = msg
                self._index = 0
            async def read(self, n:int = 1) -> str:
                if self._index + 1 >= len(self.msg):
                    return ""
                ret = self.msg[self._index:self._index+n]
                self._index += n
                await asyncio.sleep(time_delta)
                return ret
            def at_eof(self) -> bool:
                return self._index + 1 >= len(self.msg)
        return await self.log_stream(level, Typewriter(msg), *args, exc_info, extra, stack_info, stacklevel)
    
    def typewriter_debug(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.typewriter_log(logging.DEBUG, msg, time_delta, *args, exc_info, extra, stack_info, stacklevel)
    
    def typewriter_info(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.typewriter_log(logging.INFO, msg, time_delta, *args, exc_info, extra, stack_info, stacklevel)
    
    def typewriter_warning(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.typewriter_log(logging.WARNING, msg, time_delta, *args, exc_info, extra, stack_info, stacklevel)
    
    def typewriter_error(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.typewriter_log(logging.ERROR, msg, time_delta, *args, exc_info, extra, stack_info, stacklevel)
    
    def typewriter_critical(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.typewriter_log(logging.CRITICAL, msg, time_delta, *args, exc_info, extra, stack_info, stacklevel)
    
    typewriter_fatal = typewriter_critical

def getLogger(name:str, substruct:list[str] = [], colormap:Optional[dict[int, str]] = None, log_level:Optional[int] = None) -> Logger:
    '''
    Get a logger
    '''
    _log = Logger(name)
    if log_level == None:
        _log.setLevel(config.varibles['log_level'])
    else:
        _log.setLevel(log_level)
    _log.addHandler(ConsoleHandler())
    _log.handlers[0].setFormatter(Formatter(substruct, colormap))
    return _log

del _ArgsType
del _ExcInfoType
del _SysExcInfoType
