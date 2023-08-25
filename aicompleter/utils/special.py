import inspect
from typing import Iterable, TypeVar
from .. import *
from .etype import getcaller, getcallerclass, getcallerclassinstance

Command = TypeVar('Command', bound='interface.Command')

def getcallercommand(stack_level:int = 1, commands: Iterable[Command] = ()):
    from .. import Handler, Command, Interface
    class_ = getcallerclass(stack_level + 1)
    if class_ == None:
        # Try directly get the caller
        caller = getcaller(stack_level + 1)
        if caller == None:
            return None
        # function defined outside of a class
        for command in commands:
            if command.callback == caller:
                return command
        return None
    if issubclass(class_, Interface):
        # function defined inside a class
        instance = getcallerclassinstance(stack_level + 1)
        if instance == None:
            # static method or class method
            caller = getcaller(stack_level + 1)
            for command in commands:
                if command.callback == caller:
                    return command
            return None
        if not isinstance(instance, Interface):
            return None
        caller = getcaller(stack_level + 1)
        for command in commands:
            if hasattr(command, '__self__') and command.__self__ == instance:
                # Get the function from the bound method
                if hasattr(command, '__func__') and command.__func__ == caller:
                    return command
        return None
    return None
