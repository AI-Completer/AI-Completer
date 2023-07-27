import asyncio
import logging
import traceback

def launch(loop:asyncio.AbstractEventLoop, logger:logging.Logger, max_try:int = 10) -> None:
    '''
    Launch the loop, will stop when all tasks are done
    '''
    async def check_loop():
        # Check if the loop is empty
        # The one task is this function
        while True:
            try:
                if len(asyncio.all_tasks(loop)) == 1:
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
