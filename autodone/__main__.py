import os
import asyncio
from autodone import *
from autodone.config import Config
from autodone.utils import ainput,aprint
from . import log

__DEBUG__:bool = False
'''
For debug
'''
os.environ.setdefault('DEBUG', "False")
if os.environ['DEBUG'] == "True":
    __DEBUG__ = True

logger = log.Logger("Main")
formatter = log.Formatter()
handler = log.ConsoleHandler()
handler.formatter = formatter
logger.addHandler(handler)
if __DEBUG__:
    logger.setLevel(log.DEBUG)
else:
    logger.setLevel(log.INFO)

_handler:Handler = None
async def main():
    # Read Config
    logger.info("Start Executing")
    if not os.path.exists("config.json"):
        logger.debug("config.json Not Found. Use default config.")
        config = Config()
    else:
        logger.debug("config.json Found. Reading config.json")
        config = Config.loadFromFile("config.json")
    config.setdefault("global.debug", False)
    if config["global.debug"]:
        __DEBUG__ = True
        os.environ['DEBUG'] = "True"
    # Console Interface
    console_interface:Interface = implements.ConsoleInterface()
    openaichat_interface:Interface = implements.openai.OpenaichatInterface()
    # Handler
    global _handler
    _handler = Handler(config)
    # await _handler.add_interface(console_interface, initialier_interface, openaichat_interface)
    await _handler.add_interface(console_interface, openaichat_interface)
    # Session
    session:Session = await _handler.new_session()
    # Start
    ret = await session.asend(Message(
        cmd='ask',
        session=session,
        dest_interface=console_interface,
        content=MultiContent("Start Your Conversation"),
    ))
    session.send(Message(
        cmd='chat',
        session=session,
        src_interface=console_interface,
        dest_interface=openaichat_interface,
        content=MultiContent(ret),
    ))

loop = asyncio.new_event_loop()
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
try:
    loop.create_task(main())
    loop.run_forever()
except KeyboardInterrupt:
    logger.info("KeyboardInterrupt")
    # loop.stop()
    # loop.run_until_complete(_handler.close())
    loop.stop()
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.run_forever()
    loop.stop()
    loop.close()
