import os
import asyncio
from aicompleter import *
from aicompleter.config import Config
from aicompleter.utils import ainput,aprint
from aicompleter.implements import ConsoleInterface
from . import log
import argparse

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

__help__='''
AI Completer
python3 -m aicompleter [subcommands/options]
[options]:
    --help: Show this help message
    --debug: Enable debug mode, default: False, if the environment variable DEBUG is set to True, this option will be ignored
    --config: Specify the config file, default: config.json
[subcommands]:
    talk: Talk with the AI
        --ai: The AI to use, default: openaichat, options: openaichat, bingai
    helper: The helper of AI Completer, this will launcher a AI assistant to help you solve the problem
        --ai: The AI to use, default: openaichat, options: openaichat, bingai

AI Completer is a tool to help you complete your work with AI.
It can be used to complete your code, complete your text, etc.

AI Completer is still in development, so it may not work well.
'''
parser = argparse.ArgumentParser(description=__help__)
parser.add_argument('--debug', action='store_true', help='Enable debug mode, default: False, if the environment variable DEBUG is set to True, this option will be ignored')
parser.add_argument('--config', type=str, default='config.json', help='Specify the config file, default: config.json')
subparsers = parser.add_subparsers(dest='subcommand', help='subcommands', description='subcommands, including:\n\ttalk: Talk with the AI\n\thelper: The helper of AI Completer, this will launcher a AI assistant to help you solve the problem')
subparsers.required = True
talk_pareser = subparsers.add_parser('talk', help='Talk with the AI')
talk_pareser.add_argument('--ai', type=str, default='openaichat', help='The AI to use, default: openaichat, options: openaichat, bingai')
helper_pareser = subparsers.add_parser('helper', help='The helper of AI Completer, this will launcher a AI assistant to help you solve the problem')
helper_pareser.add_argument('--ai', type=str, default='openaichat', help='The AI to use, default: openaichat, options: openaichat, bingai')

args = parser.parse_args()
if args.debug:
    __DEBUG__ = True
    os.environ['DEBUG'] = "True"

if not os.path.exists(args.config):
    logger.debug("config.json Not Found. Use default config.")
    config_ = Config()
else:
    logger.debug(f"{args.config} Found. Reading configure")
    config_ = Config.loadFromFile(args.config)
config_.setdefault("global.debug", False)
if config_["global.debug"]:
    __DEBUG__ = True
    os.environ['DEBUG'] = "True"

__AI_map__ = {
    'openaichat': (ai.openai.Chater, config_['openaichat']),
    'bingai': (ai.bing.BingAI, config_['bingai']),
}

async def main():
    # Analyse args
    logger.info("Start Executing")
    match args.subcommand:
        case 'talk':
            ai_name = args.ai
            if ai_name not in __AI_map__:
                logger.fatal(f"AI {ai_name} not found.")
                return
            ai_cls, ai_config = __AI_map__[ai_name]
            ai_config.setdefault(config_.global_)
            ai_ = ai_cls(ai_config)
            ai_interface = ai.ChatInterface(ai=ai_, namespace=ai_name)
            con_interface = ConsoleInterface()
            handler_ = Handler(config_)
            await handler_.add_interface(ai_interface, con_interface)
            session_ = await handler_.new_session()

            usercontent = None
            await aprint("Please Start Your Conversation")
            while True:
                usercontent = await ainput(">>> ")
                ret:str = await session_.send(Message(
                    content = usercontent,
                    cmd = 'ask',
                    dest_interface=ai_interface,
                ))
                await aprint(ret)
        case 'helper':
            raise NotImplementedError("Helper is not implemented yet")

loop = asyncio.new_event_loop()
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
try:
    loop.create_task(main())
    loop.run_forever()
except KeyboardInterrupt:
    logger.warn("KeyboardInterrupt")
    loop.stop()
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.run_forever()
    loop.stop()
    loop.close()
