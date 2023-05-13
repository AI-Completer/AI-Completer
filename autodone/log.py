'''
Custom logging module
'''
import logging
from typing import Iterable, Optional
import colorama

CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
ERROR = logging.ERROR
WARNING = logging.WARNING
WARN = logging.WARN
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET

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
        nrecord.asctime = colorama.Fore.BLACK + colorama.Style.BRIGHT + self.formatTime(record, self.datefmt) + colorama.Fore.RESET
        nrecord.levelname = self.getColor(record.levelno) + record.levelname + colorama.Fore.RESET
        nrecord.name = colorama.Fore.WHITE + record.name + colorama.Fore.RESET
        nrecord.message = colorama.Fore.WHITE + record.getMessage() + colorama.Fore.RESET

        self._fmt = "{asctime} - " + \
            "{levelname:6}" + \
            " [{name}]" + "".join([
            f"[{sub}]" for sub in self.substruct
        ]) + " {message}"

        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        return self._fmt.format(**nrecord.__dict__)

ConsoleHandler = logging.StreamHandler

# class ConsoleHandler(logging.Handler):
#     '''
#     Custom handler
#     eg. Handler('interface')
#     '''
#     def __init__(self,colormap:Optional[dict[int,str]] = None):
#         self.colormap = {
#             logging.DEBUG: colorama.Fore.WHITE,
#             logging.INFO: colorama.Fore.GREEN,
#             logging.WARNING: colorama.Fore.YELLOW,
#             logging.ERROR: colorama.Fore.RED,
#             logging.CRITICAL: colorama.Fore.RED + colorama.Style.BRIGHT
#         }
#         if colormap:
#             self.colormap.update(colormap)
#         colorama.init()
#         super().__init__()

#     def emit(self, record:logging.LogRecord) -> None:
#         '''
#         Emit the record
#         '''
#         print(self.colormap[int(record.levelno / 10) * 10] + self.format(record) + colorama.Fore.RESET)

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

def getLogger(name:str) -> Logger:
    '''
    Get a logger
    '''
    return Logger(name)
