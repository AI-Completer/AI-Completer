'''
Custom logging module
'''

import logging
import os
import colorama

from typing import Iterable, Optional

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
        nrecord.message = record.getMessage()
        nrecord.asctime = colorama.Fore.BLACK + colorama.Style.DIM + self.formatTime(record, self.datefmt) + colorama.Fore.RESET + colorama.Style.RESET_ALL
        nrecord.levelname = self.getColor(record.levelno) + record.levelname + colorama.Fore.RESET
        nrecord.name = colorama.Fore.WHITE + colorama.Style.DIM + record.name + colorama.Fore.RESET + colorama.Style.RESET_ALL
        nrecord.message = colorama.Fore.WHITE + record.getMessage() + colorama.Fore.RESET

        self._fmt = \
            "{asctime} - " + \
            "{levelname:>6}" + \
            " [{name}]" + "".join([
            f"[{colorama.Fore.WHITE + colorama.Style.DIM + sub + colorama.Fore.RESET + colorama.Style.RESET_ALL}]" 
                for sub in self.substruct
        ]) + " {message}"

        # nrecord {}
        nrecord.message = nrecord.message.replace('{','{{').replace('}','}}')

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

def getLogger(name:str, substruct:list[str] = [], colormap:Optional[dict[int, str]] = None, debug:Optional[bool] = None) -> Logger:
    '''
    Get a logger
    '''
    _log = Logger(name)
    if debug == None:
        _log.setLevel(logging.DEBUG if bool(os.environ.get('DEBUG', False)) else logging.INFO)
    else:
        _log.setLevel(logging.DEBUG if debug else logging.INFO)
    _log.addHandler(ConsoleHandler())
    _log.handlers[0].setFormatter(Formatter(substruct, colormap))
    return _log
