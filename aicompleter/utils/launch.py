import asyncio
import logging
import traceback
from typing import Optional

def launch(loop:asyncio.AbstractEventLoop, logger:logging.Logger, max_try:int = 10) -> None:
    '''
    Launch the loop
    
    This function will stop the loop when all tasks are done
    '''
    async def check_loop():
        # Check if the loop is empty
        # The one task is this function
        while True:
            try:
                running_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
                if len(running_tasks) == 1:
                    loop.stop()
                    return
                else:
                    await asyncio.sleep(0)
            except asyncio.CancelledError as e:
                return
            except KeyboardInterrupt:
                loop.stop()
                logger.critical("KeyboardInterrupt")
                await asyncio.sleep(0)
    expecttasks = {loop.create_task(check_loop())}

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.critical("KeyboardInterrupt")
    except BaseException as e:
        logger.critical(f"Unexception: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            traceback.print_exc()
    finally:
        if not loop.is_closed():
            exception_tasks = [task for task in asyncio.all_tasks(loop) if task.done() and task.exception() != None]
            if len(exception_tasks) > 0:
                logger.critical(f"Exception tasks: {exception_tasks!r}")
                # remove them
                for task in exception_tasks:
                    task.cancel()
                
            try_time = 0
            while not all(task.done() for task in asyncio.all_tasks(loop) if task not in expecttasks) and try_time < max_try:
                try_time += 1
                for task in asyncio.all_tasks(loop):
                    if task in expecttasks:
                        continue
                    task.cancel()
                try:
                    loop.run_forever()
                except BaseException as e:
                    logger.critical(f"Unexception: {e}")
                    if logger.isEnabledFor(logging.DEBUG):
                        traceback.print_exc()
                
                exception_tasks = [task for task in asyncio.all_tasks(loop) if task.done() and task.exception() != None]
                if len(exception_tasks) > 0:
                    logger.critical(f"Exception tasks: {exception_tasks!r}")
                    for task in exception_tasks:
                        task.cancel()

            if try_time >= max_try:
                logger.critical("Force Quit")
            else:
                # Stop excepted tasks
                need_run = any(task.cancel() for task in expecttasks)
                if need_run:
                    try:
                        loop.run_until_complete(asyncio.gather(*expecttasks))
                    except BaseException as e:
                        logger.critical(f"Unexception: {e}")
                        if logger.isEnabledFor(logging.DEBUG):
                            traceback.print_exc()

def start(*tasks: asyncio.Future, loop:Optional[asyncio.AbstractEventLoop] = None, logger:Optional[logging.Logger] = None):
    '''
    Start the tasks

    This should be called only in the main module
    '''
    from .. import log
    if loop==None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    intasks:list[asyncio.Task] = []
    for task in tasks:
        intasks.append(loop.create_task(task))
    logger = logger or log.getLogger('main')
    launch(loop=loop, logger=logger)
    for task in intasks:
        if task.cancelled():
            continue
        if task.done() and task.exception() != None:
            logger.debug(f"Task {task!r} has exception: {task.exception()!r}")

def run_handler(entry: asyncio.Future, handler, loop:Optional[asyncio.AbstractEventLoop] = None, logger: Optional[logging.Logger] = None):
    '''
    Run the handler

    This should be called only in the main module
    '''
    from .. import Handler, log
    if not isinstance(handler, Handler):
        raise TypeError(f"Invalid handler type: {handler!r}")
    if logger == None:
        logger = log.getLogger('main')
    if loop != None:
        if handler._loop != None and handler._loop != loop:
            logger.warning(f"Handler's loop is not None and not equal to the given loop, use the given loop")
            handler._loop.close()
        handler._loop = loop
    else:
        loop = handler._loop
    start(entry, loop=loop, logger=logger)
    loop = loop or asyncio.get_event_loop()
    loop.create_task(handler.close())
    launch(loop=loop, logger=logger)
