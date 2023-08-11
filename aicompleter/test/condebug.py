'''
Console Debug Module

This module will try to execute the command typed in console,
And print the result to console
'''

from asyncio import iscoroutine
import asyncio
from typing import Optional

from .. import Interface, utils, Handler, Config, InterfaceDiGraph, log, Commands, Command

logger = log.getLogger('debug-main')
logger.setLevel(log.DEBUG)

def run_handler(handler:Handler, config:Optional[Config] = None,*, loop:Optional[asyncio.AbstractEventLoop] = None):
    if loop == None:
        loop = asyncio.new_event_loop()
    async def start():
        session = await handler.new_session(config)
        # start the command line
        
        while True:
            command = input('>>> ')
            if command.startswith("!"):
                # internal command
                if command == "!exit":
                    break
                elif command == "!help":
                    print("Internal command:")
                    print("!exit: Exit the console")
                    print("!help: Show this message")
                    print("!session: Show the session info")
                    print("!command: Show the interface command")
                    print("!execute: Directly execute python code")
                    print("Interface command execution:")
                    print("<command> <args>")
                elif command == "!session":
                    print("ID:", session.id)
                elif command == "!command":
                    print("Commands:")
                    for cmd in handler.get_executable_cmds():
                        print(cmd.cmd, cmd.description, cmd.format.json_text, sep='\t\t')
                elif command == "!execute":
                    code = input("Python: >>> ")
                    try:
                        ret = exec(code, globals(), locals())
                    except Exception as e:
                        logger.exception("Error when execute code: %s", str(e))
                    else:
                        if iscoroutine(ret):
                            try:
                                ret = await ret
                            except Exception as e:
                                logger.exception("Error when execute code: %s", str(e))
                        logger.info("Result: %r", ret)
                else:
                    print("Unknown command, type !help for help")
            else:
                # interface command
                cmd = command.split(maxsplit=1)
                if len(cmd) > 1:
                    cmd, arg = cmd[0], cmd[1]
                else:
                    cmd, arg = cmd[0], ''
                try:
                    ret = await session.asend(cmd, arg)
                except Exception as e:
                    logger.exception("Error when execute command %r: %s", command, str(e))
                else:
                    logger.info("Result: %r", ret)

        # close the session
        try:
            await session.close()
        except Exception as e:
            logger.exception("Error when close the session: %s", str(e))
            # Force remove
            logger.warning("Force remove the session")
            handler._running_sessions.remove(session)
    
    handler.on_exception.add_callback(lambda event, e: logger.exception("Error when handle the exception: %s", str(e)))

    loop.create_task(start())
    try:
        utils.launch(loop=loop, logger=logger)
    except Exception as e:
        logger.fatal("Fatal error when launch the loop: %s", str(e))
        logger.fatal("Shutting down...")
        loop.close()
        return

    loop.create_task(handler.close())
    try:
        utils.launch(loop=loop, logger=logger)
    except Exception as e:
        logger.fatal("Fatal error when launch the loop: %s", str(e))
        logger.fatal("Shutting down...")
        loop.close()
        return
    
    logger.info("Shutting down...")
    loop.close()

def run_interface(target:Interface, *dependencies:Interface, config:Optional[Config] = None, loop:Optional[asyncio.AbstractEventLoop] = None):
    '''
    Run an interface

    When the interface is running, you can type commands in console,
    the internal command is started with '!', you can operate the interface
    '''
    if loop == None:
        loop = asyncio.new_event_loop()
    handler = Handler(config or Config())
    async def _():
        graph = InterfaceDiGraph()
        for dependency in dependencies:
            graph.add(target, dependency)
        try:
            await graph.setup(handler)
        except Exception as e:
            logger.exception("Error when setup graph, it seems to be a problem when initialize the interface: %s", str(e))
            return e
    ret = loop.run_until_complete(_())
    if isinstance(ret, Exception):
        logger.fatal("Fatal error when setup the graph: %s", str(ret))
        logger.fatal("Shutting down...")
        loop.close()
        return
    run_handler(handler, config, loop=loop)

def run_command(command:Command, *dependencies:Interface, config:Optional[Config] = None, loop:Optional[asyncio.AbstractEventLoop] = None):
    '''
    Run a command

    When the command is running, you can type commands in console,
    the internal command is started with '!', you can operate the interface
    '''
    class TempInterface(Interface):
        cmdreg:Commands = Commands()
        cmdreg.register(command)

    run_interface(TempInterface(), *dependencies, config=config, loop=loop)
