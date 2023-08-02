'''
Custom logging module
'''

import asyncio
import copy
import functools
import logging
import os
import sys
from collections.abc import Mapping
from types import TracebackType
from typing import Any, Iterable, Optional, TypeAlias
from . import config
from .utils.etype import hookclass

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

defaultLevelColorMap: dict[int, str] = {
    logging.DEBUG: colorama.Fore.BLUE,
    logging.INFO: colorama.Fore.GREEN,
    logging.WARNING: colorama.Fore.YELLOW,
    logging.ERROR: colorama.Fore.RED,
    logging.CRITICAL: colorama.Fore.RED + colorama.Style.BRIGHT
}
defaultColorMap: dict[str, str] = {
    'asctime': colorama.Fore.BLACK + colorama.Style.DIM,
    'name': colorama.Fore.WHITE + colorama.Style.DIM,
    'message': colorama.Fore.WHITE,
    'substruct': colorama.Fore.WHITE + colorama.Style.DIM,
}

class LogRecord(logging.LogRecord):
    '''
    Custom LogRecord
    '''
    def __init__(self, name:str, level:int, pathname:str, lineno:int, msg:object, args:_ArgsType, exc_info:_ExcInfoType, func:str, sinfo:str, substruct:list[str] = [], **kwargs: object) -> None:
        super().__init__(name, level, pathname, lineno, msg, args, exc_info, func, sinfo, **kwargs)
        self.substruct:list[str] = substruct

    def __repr__(self) -> str:
        return f"<LogRecord: name={self.name} level={self.levelname} substruct=[{','.join(self.substruct)}] msg={self.msg}>"
    
class ColorStrFormatStyle(logging.StrFormatStyle):
    '''
    Custom StrFormatStyle
    '''

    def __init__(self, fmt: str, *, defaults: Mapping[str, Any] | None = None, colormap: Optional[dict[str, str]] = None, levelcolormap: Optional[dict[int, str]] = None) -> None:
        super().__init__(fmt, defaults=defaults)
        self._colormap = defaultColorMap
        if colormap:
            self._colormap.update(colormap)
        self._levelcolormap = defaultLevelColorMap
        if levelcolormap:
            self._levelcolormap.update(levelcolormap)

    def _format(self, record: LogRecord):
        if defaults := self._defaults:
            values = defaults | record.__dict__
        else:
            values = record.__dict__
        for key, value in values.items():
            if isinstance(value, str) and key in self._colormap:
                values[key] = self._colormap.get(key) + value + colorama.Fore.RESET + colorama.Style.RESET_ALL
        # levelname
        values['levelname'] = self._levelcolormap[int(record.levelno / 10) * 10] + values['levelname'] + colorama.Fore.RESET + colorama.Style.RESET_ALL

        if 'substruct' in values:
            values['substruct'] = "".join([
                f"[{self._colormap['substruct'] + sub + colorama.Fore.RESET + colorama.Style.RESET_ALL}]" 
                    for sub in values['substruct']
                ])
        return self._fmt.format(**values)

class Formatter(logging.Formatter):
    '''
    Custom formatter
    '''
    def __init__(self, style:logging.PercentStyle, datefmt: str | None = None, validate: bool = True) -> None:
        self._style = style
        if validate:
            self._style.validate()
        self._fmt = self._style._fmt
        self.datefmt = datefmt

StreamHandler: TypeAlias = logging.StreamHandler

class Logger(logging.Logger):
    '''
    Custom logger
    '''
    def __init__(self, name:str, level:int = logging.NOTSET, substruct:list[str] = []):
        super().__init__(name, level)
        self._stack = copy.copy(substruct)

    def push(self, name:str) -> None:
        '''
        Push a name to stack
        '''
        self._stack.append(str(name))

    def pop(self) -> str:
        '''
        Pop a name from stack
        '''
        ret = self._stack.pop()
        return ret

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        """
        Make Record
        Use custom LogRecord class
        """
        rv = LogRecord(name, level, fn, lno, msg, args, exc_info, func,
                             sinfo, self._stack)
        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in rv.__dict__):
                    raise KeyError("Attempt to overwrite %r in LogRecord" % key)
                rv.__dict__[key] = extra[key]
        return rv
    
    async def log_stream(self, level: int, msg: asyncio.StreamReader, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1) -> None:
        if not self.isEnabledFor(level):
            return
        async with _on_reading:
            # Record the console cursor
            print("\033[s",end="")
            # Get console formater
            formatter = None
            for handler in self.handlers:
                if isinstance(handler, StreamHandler) and StreamHandler.stream == sys.stdout:
                    formatter = handler.formatter
                    break
            # Stream the log
            output = ""
            srcfile = os.path.normcase(__file__)
            while True:
                addchar = await msg.read(1)
                output += addchar
                # Move the cursor to the recorded position
                print("\033[u",end="",flush=True)
                if addchar == "":
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

    def debug_stream(self, msg: asyncio.StreamReader, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.DEBUG, msg, *args, exc_info, extra, stack_info, stacklevel)
    
    def info_stream(self, msg: asyncio.StreamReader, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.INFO, msg, *args, exc_info, extra, stack_info, stacklevel)
    
    def warning_stream(self, msg: asyncio.StreamReader, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.WARNING, msg, *args, exc_info, extra, stack_info, stacklevel)
    
    def error_stream(self, msg: asyncio.StreamReader, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.ERROR, msg, *args, exc_info, extra, stack_info, stacklevel)
    
    def critical_stream(self, msg: asyncio.StreamReader, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.CRITICAL, msg, *args, exc_info, extra, stack_info, stacklevel)
    
    fatal_stream = critical_stream

    async def typewriter_log(self, level: int, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1) -> None:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader(limit=1, loop=loop)
        task = loop.create_task(self.log_stream(level, reader, *args, exc_info, extra, stack_info, stacklevel))
        for char in msg:
            await asyncio.sleep(time_delta)
            reader.feed_data(char.encode())
        reader.feed_eof()
        await task
    
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

_common_handlers = [
    StreamHandler()
]
_common_handlers[0].setFormatter(Formatter(ColorStrFormatStyle(
    "{asctime} - {levelname} [{name}]{substruct} {message}"
)))

def configHandlers(handlers:Iterable[logging.Handler]) -> None:
    '''
    Config handlers
    '''
    global _common_handlers
    _common_handlers = handlers

root = Logger('ROOT')
root.handlers = _common_handlers

def getLogger(name:str, substruct:list[str] = []) -> Logger:
    '''
    Get a logger
    '''
    # _log = Logger(name, substruct=substruct)
    # if level != None:
    #     _log.setLevel(level)
    # else:
    #     _log.setLevel(config.varibles['log_level'])
    # _log.handlers = _common_handlers

    # Below is a hack to make the logger share a same class and level
    _log = hookclass(root, {
        'name': name,
        '_stack': copy.copy(substruct),
    })
    return _log

del _ArgsType
del _ExcInfoType
del _SysExcInfoType
