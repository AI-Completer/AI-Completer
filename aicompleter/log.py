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
from typing import Any, Callable, Coroutine, Iterable, Optional, TypeAlias

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

_SysExcInfoType = tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None]
_ExcInfoType = None | bool | _SysExcInfoType | BaseException
_ArgsType = tuple[object, ...] | Mapping[str, object]

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

    def format(self, record: LogRecord):
        record = copy.copy(record)
        try:
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
        except KeyError as e:
            raise ValueError('Formatting field not found in record: %s' % e)

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

class StreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        if stream == None:
            stream = sys.stdout     # Just set stdout as default
        super().__init__(stream)

class Logger(logging.Logger):
    '''
    Custom logger
    '''
    def __init__(self, name:str, level:int = logging.NOTSET, substruct:list[str] = []):
        super().__init__(name, level)
        self._stack = copy.copy(substruct)

    def push(self, name:str | Iterable[str]) -> None:
        '''
        Push a name to stack
        '''
        if isinstance(name, str):
            self._stack.append(str(name))
        else:
            for n in name:
                self._stack.append(str(n))

    def pop(self):
        '''
        Pop a name from stack
        '''
        return self._stack.pop()

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
    
    def debug_function(self, func:Optional[Callable] = None, **kwargs) -> None:
        '''
        Log the function call

        This will import the package outside the stdlib, if the `func` is not provided, the function name will be guessed from the stack frame
        '''
        if not self.isEnabledFor(DEBUG):
            # There is no need to log
            return
        if func:
            if kwargs:
                self.debug(f"Calling {func.__name__} with {kwargs}")
                return
            from .utils.etype import getframe
            from .utils.typeval import get_signature
            sig = get_signature(func)
            frame = getframe(1)
            # match the parameters
            locals_ = frame.f_locals
            kwparams = {}
            for name in sig.parameters:
                if name in frame.f_locals:
                    kwparams[name] = locals_[name]
            self.debug(f"Calling {func.__name__} with {kwparams}")
        else:
            from .utils.etype import getframe
            frame = getframe(1)
            if kwargs:
                self.debug(f"Calling {frame.f_code.co_name} with {kwargs}")
                return
            # function object may be ungettable, we don't match the parameters
            self.debug(f"Calling {frame.f_code.co_name} with {frame.f_locals}")
    
    async def log_stream(self, level: int, msg: asyncio.StreamReader, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1) -> None:
        '''
        Log the stream

        Note
        ----
        There are some bugs on this function: mutli-lines message support
        '''
        if not self.isEnabledFor(level):
            return
        from .utils.aio import aiterfunc
        async with _on_reading:
            # Record the console cursor
            print("\033[s",end="")
            # Get console formater
            formatter = None
            c = self
            while c:
                for handler in c.handlers:
                    if isinstance(handler, StreamHandler) and handler.stream in (sys.stdout, sys.stderr):
                        formatter = handler.formatter
                        break
                if formatter:
                    break
                if c.propagate:
                    c = c.parent
                else:
                    c = None
            
            if formatter == None:
                raise Exception('StreamHandler logger not found')
            # Stream the log
            output = b""
            srcfile = os.path.normcase(__file__)
            async for addchar in aiterfunc(functools.partial(msg.read, 1), b''):
                output += addchar
                try:
                    decode_value = output.decode()
                except UnicodeDecodeError:
                    continue
                # Move the cursor to the recorded position
                print("\033[u",end="",flush=True)
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
                record = self.makeRecord(self.name, level, fn, lno, decode_value, (),
                                        exc_info, func, extra, sinfo)
                print(formatter.format(record), end="", flush=True)
            
            # Move the cursor to the recorded position
            print("\033[u",end="",flush=True)
            # Use the original log function to log the output
            self.handle(record)

    def debug_stream(self, msg: asyncio.StreamReader, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.DEBUG, msg, exc_info, extra, stack_info, stacklevel)
    
    def info_stream(self, msg: asyncio.StreamReader, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.INFO, msg, exc_info, extra, stack_info, stacklevel)
    
    def warning_stream(self, msg: asyncio.StreamReader, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.WARNING, msg, exc_info, extra, stack_info, stacklevel)
    
    def error_stream(self, msg: asyncio.StreamReader, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.ERROR, msg, exc_info, extra, stack_info, stacklevel)
    
    def critical_stream(self, msg: asyncio.StreamReader, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1):
        return self.log_stream(logging.CRITICAL, msg, exc_info, extra, stack_info, stacklevel)
    
    fatal_stream = critical_stream

    async def typewriter_log(self, level: int, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1, loop: Optional[asyncio.AbstractEventLoop] = None) -> Coroutine[None, None, None]:
        '''
        Log just like a typewriter
        '''
        if not self.isEnabledFor(level):
            # no need to log and wait
            return
        loop = loop or asyncio.get_event_loop()
        reader = asyncio.StreamReader(limit=1, loop=loop)
        task = loop.create_task(self.log_stream(level, reader, exc_info, extra, stack_info, stacklevel))
        for char in (msg % args):
            await asyncio.sleep(time_delta)
            reader.feed_data(char.encode())
        reader.feed_eof()
        await task
    
    def typewriter_debug(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1, loop: Optional[asyncio.AbstractEventLoop] = None):
        return self.typewriter_log(logging.DEBUG, msg, time_delta, *args, exc_info = exc_info, extra = extra, stack_info = stack_info, stacklevel = stacklevel, loop = loop)
    
    def typewriter_info(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1, loop: Optional[asyncio.AbstractEventLoop] = None):
        return self.typewriter_log(logging.INFO, msg, time_delta, *args, exc_info = exc_info, extra = extra, stack_info = stack_info, stacklevel = stacklevel, loop = loop)
    
    def typewriter_warning(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1, loop: Optional[asyncio.AbstractEventLoop] = None):
        return self.typewriter_log(logging.WARNING, msg, time_delta, *args, exc_info = exc_info, extra = extra, stack_info = stack_info, stacklevel = stacklevel, loop = loop)
    
    def typewriter_error(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1, loop: Optional[asyncio.AbstractEventLoop] = None):
        return self.typewriter_log(logging.ERROR, msg, time_delta, *args, exc_info = exc_info, extra = extra, stack_info = stack_info, stacklevel = stacklevel, loop = loop)
    
    def typewriter_critical(self, msg: str, time_delta:float = 0.1, *args: object, exc_info: _ExcInfoType = None, extra: Mapping[str, object] | None = None, stack_info: bool = False, stacklevel: int = 1, loop: Optional[asyncio.AbstractEventLoop] = None):
        return self.typewriter_log(logging.CRITICAL, msg, time_delta, *args, exc_info = exc_info, extra = extra, stack_info = stack_info, stacklevel = stacklevel, loop = loop)
    
    typewriter_fatal = typewriter_critical

root = Logger('ROOT')
root.propagate = False
root.setLevel(WARNING)

Logger.root = root
Logger.manager = logging.Manager(Logger.root)
Logger.manager.setLoggerClass(Logger)
Logger.manager.setLogRecordFactory(LogRecord)

colorstyle = Formatter(ColorStrFormatStyle(
    "{asctime} - {levelname} [{name}]{substruct} {message}"
))
consolehandler = StreamHandler()
consolehandler.setFormatter(colorstyle)
root.handlers.append(consolehandler)

setLevel = root.setLevel
debug = root.debug
info = root.info
warning = root.warning
warn = root.warn
error = root.error
critical = root.critical
fatal = root.fatal

def getLogger(name:str, substruct:list[str] = []) -> Logger:
    '''
    Get a logger
    '''
    _log = Logger(name, substruct=substruct)
    _log.parent = root
    return _log

__all__ = (
    'CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'DEBUG', 'NOTSET',
    'StreamHandler', 'Logger', 'getLogger', 'setLevel', 'debug', 'info', 'warning', 'warn', 'error', 'critical', 'fatal',
    'root', 'Formatter', 'ColorStrFormatStyle', 'LogRecord', 'defaultColorMap', 'defaultLevelColorMap'
)
