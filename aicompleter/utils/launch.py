import asyncio
import logging
import traceback

def launch(loop:asyncio.AbstractEventLoop, logger:logging.Logger, max_try:int = 10, expecttasks: set[asyncio.Task] = set()) -> None:
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
                    if task not in expecttasks:
                        continue
                    task.cancel()
                loop.run_forever()

            if try_time >= max_try:
                logger.critical("Force Quit")
            else:
                # Stop excepted tasks
                need_run = any(task.cancel() for task in expecttasks)
                if need_run:
                    loop.run_until_complete(asyncio.gather(*expecttasks))
            loop.close()
