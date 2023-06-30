import argparse
import asyncio
import os

from . import config
from .config import Config
from . import log

__DEBUG__:bool = False
'''
For debug
'''
os.environ.setdefault('DEBUG', "False")
if os.environ['DEBUG'] == "True":
    __DEBUG__ = True

logger = log.getLogger("Main")

__help__='''
AI Completer
python3 -m aicompleter [options] [subcommands] [subcommand options]
[options]:
    --help: Show this help message
    --debug: Enable debug mode, default: False, if the environment variable DEBUG is set to True, this option will be ignored
    --config: Specify the config file, default: config.json
[subcommands]:
    talk: Talk with the AI
        --ai: The AI to use, default: openaichat, options: openaichat, bingai
    helper: The helper of AI Completer, this will launcher a AI assistant to help you solve the problem
        --ai: The AI to use, default: openaichat, options: openaichat, bingai
        --enable-agent: Enable subagent, default: False
        --include [interface]: Include the extra interface, default: None, options: pythoncode
            # Note: AI interface will be included automatically

AI Completer is a tool to help you complete your work with AI.
It can be used to complete your code, complete your text, etc.

AI Completer is still in development, so it may not work well.
'''
parser = argparse.ArgumentParser(description=__help__)
parser.add_argument('--debug', action='store_true', help='Enable debug mode, default: False, if the environment variable DEBUG is set to True, this option will be ignored')
parser.add_argument('--config', type=str, default='config.json', help='Specify the config file, default: config.json')
parser.add_argument('--disable-memory', action='store_true', help='Disable memory, default: False', dest='disable_memory')
parser.add_argument('--disable-faiss', action='store_true', help='Disable faiss, default: False', dest='disable_faiss')
subparsers = parser.add_subparsers(dest='subcommand', help='subcommands', description='subcommands, including:\n\ttalk: Talk with the AI\n\thelper: The helper of AI Completer, this will launcher a AI assistant to help you solve the problem')
subparsers.required = True
talk_pareser = subparsers.add_parser('talk', help='Talk with the AI')
talk_pareser.add_argument('--ai', type=str, default='openaichat', choices=('openaichat', 'bingai'), help='The AI to use, default: openaichat, options: openaichat, bingai')
helper_pareser = subparsers.add_parser('helper', help='The helper of AI Completer, this will launcher a AI assistant to help you solve the problem')
helper_pareser.add_argument('--ai', type=str, default='openaichat', choices=('openaichat', 'bingai'), help='The AI to use, default: openaichat, options: openaichat, bingai')
helper_pareser.add_argument('--enable-agent', action='store_true', help='Enable subagent, default: False', dest='enable_agent')
helper_pareser.add_argument('-i','--include', type=str, nargs='+', default=[], choices=('pythoncode'), help='Include the extra interface, default: None, options: pythoncode')

args = parser.parse_args()
if args.debug:
    __DEBUG__ = True

if not os.path.exists(args.config):
    logger.info("config.json Not Found. Use default config.")
    config_ = Config()
else:
    logger.info(f"{args.config} Found. Reading configure")
    config_ = Config.loadFromFile(args.config)
config_.setdefault("global.debug", False)
if config_["global.debug"]:
    __DEBUG__ = True

if __DEBUG__ == True:
    logger.setLevel(log.DEBUG)
    logger._cache = {}              # Issue: The logging cache will not be cleared when the logger level is changed
    logger.debug("Debug Mode Enabled")
    config.varibles['debug'] = True
    config.varibles['log_level'] = log.DEBUG

if args.disable_memory:
    config.varibles['disable_memory'] = True
if args.disable_faiss:
    config.varibles['disable_faiss'] = True



# After the initialization of the arguments and global configuration, we can now import the modules and do the real work
from aicompleter import *
from aicompleter.implements import ConsoleInterface
from aicompleter.utils import ainput, aprint

__AI_map__ = {
    'openaichat': (ai.openai.Chater, {"config":config_['openaichat'], "model":'gpt-3.5-turbo'}),
    'bingai': (ai.microsoft.BingAI, {"config":config_['bingai']}),
}
__Int_map__ = {
    'pythoncode': implements.PythonCodeInterface,
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
            ai_cls, ai_param = __AI_map__[ai_name]
            ai_param["config"].setdefault(config_.global_)
            ai_ = ai_cls(**ai_param)
            ai_interface = ai.ChatInterface(ai=ai_, namespace=ai_name)
            con_interface = ConsoleInterface()
            handler_ = Handler(config_)
            await handler_.add_interface(ai_interface, con_interface)
            session_ = await handler_.new_session()

            usercontent = None
            await aprint("Please Start Your Conversation")
            while True:
                usercontent = await ainput(">>> ")
                ret:str = await session_.asend(Message(
                    content = usercontent,
                    cmd = 'ask',
                    dest_interface=ai_interface,
                ))
                await aprint(ret)
        case 'helper':
            _handler = Handler(config_)
            ai_name = args.ai
            if ai_name not in __AI_map__:
                logger.critical(f"AI {ai_name} not found.")
                return
            ai_cls, ai_param = __AI_map__[ai_name]
            ai_param["config"].setdefault(config_.global_)
            ai_ = ai_cls(**ai_param)

            ai_interface = (implements.logical.SelfStateExecutor if args.enable_agent else implements.logical.StateExecutor)(ai=ai_, namespace=ai_name)
            
            console_interface = ConsoleInterface()
            graph = layer.InterfaceDiGraph()
            graph.add(ai_interface, console_interface)

            for interface_name in args.include:
                if interface_name not in __Int_map__:
                    logger.critical(f"Interface {interface_name} not found.")
                    return
                graph.add(ai_interface, __Int_map__[interface_name]())

            await graph.setup(_handler)
            new_session = await _handler.new_session()

            ret = await new_session.asend(Message(
                content = 'Please Start Your Conversation',
                cmd = 'ask',
                dest_interface=console_interface,
            ))
            await new_session.asend(Message(
                content = ret,
                cmd = 'agent',
                dest_interface=ai_interface,
            ))

loop = asyncio.new_event_loop()
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
async def check_loop():
    # Check if the loop is empty
    # The one task is this function
    while True:
        try:
            if len(asyncio.all_tasks(loop)) == 1:
                loop.stop()
                await asyncio.sleep(0)
            else:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError as e:
            loop.stop()
            return
try:
    loop.create_task(main())
    check_task = loop.create_task(check_loop())
    loop.run_forever()
except KeyboardInterrupt:
    logger.critical("KeyboardInterrupt")
    max_try = 10
    try_time = 0
    while not all(task.done() for task in asyncio.all_tasks(loop) if task != check_task) and try_time < max_try:
        try_time += 1
        for task in asyncio.all_tasks(loop):
            if task == check_task:
                continue
            task.cancel()
        loop.run_forever()

    if try_time >= max_try:
        logger.critical("Force Quit")
    # Stop check_task
    check_task.cancel()
    loop.run_until_complete(check_task)
    loop.close()
logger.debug("Loop Closed")
