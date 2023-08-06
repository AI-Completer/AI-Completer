import argparse
import asyncio
import importlib
import os
import sys
import traceback

from .common import serialize
from . import config
from .config import Config
from . import log

if sys.version_info < (3, 11):
    raise RuntimeError("Python 3.11+ is required")

__DEBUG__:bool = False
'''
For debug
'''
os.environ.setdefault('DEBUG', "False")
if os.environ['DEBUG'] == "True":
    __DEBUG__ = True

# Note: logger is shared, and the level would be global setting
logger = log.getLogger("main")
logger.setLevel(log.INFO)
if __DEBUG__ == True:
    logger.setLevel(log.DEBUG)

__help__='''
AI Completer
An AI assistant to help you complete your work
'''
parser = argparse.ArgumentParser(description=__help__)
parser.add_argument('--debug', action='store_true', help='Enable debug mode, if the environment variable DEBUG is set to True, this option will be ignored')
parser.add_argument('--config', type=str, default='config.json', help='Specify the config file, default: config.json')
parser.add_argument('--history', type=str, default='history.json', help='Specify the history file, default: history.json')
parser.add_argument('--load-history', action='store_true', help='Load history without asking for user. This is priorer than --disable-history', dest='load_history')
parser.add_argument('--save-history', action='store_true', help='Save history without asking for user. This is priorer than --disable-history', dest='save_history')
parser.add_argument('--disable-history', action='store_true', help='Disable history', dest='disable_history')
parser.add_argument('--enable-memory', action='store_true', help='Enable memory', dest='enable_memory')
# parser.add_argument('--disable-faiss', action='store_true', help='Disable faiss', dest='disable_faiss')
subparsers = parser.add_subparsers(dest='subcommand', help='subcommands', description='subcommands, including:\n\ttalk: Talk with the AI\n\thelper: The helper of AI Completer, this will launcher a AI assistant to help you solve the problem')
subparsers.required = True
talk_pareser = subparsers.add_parser('talk', help='Talk with the AI')
talk_pareser.add_argument('--ai', type=str, default='openaichat', choices=('openaichat', 'bingai'), help='The AI to use, default: openaichat, options: openaichat, bingai')
talk_pareser.add_argument('--model', type=str, default='', help='The model to use, the choices differ from the AI, default: not set, options: openaichat: davinci, curie ,..., bingai: balanced, creative, precise')
helper_pareser = subparsers.add_parser('helper', help='The helper of AI Completer, this will launcher a AI assistant to help you solve the problem')
helper_pareser.add_argument('--ai', type=str, default='openaichat', choices=('openaichat', 'bingai'), help='The AI to use, default: openaichat, options: openaichat, bingai')
helper_pareser.add_argument('--model', type=str, default='', help='The model to use, the choices differ from the AI, default: not set, options: openaichat: davinci, curie ,..., bingai: balanced, creative, precise')
helper_pareser.add_argument('--enable-agent', action='store_true', help='Enable subagent', dest='enable_agent')
helper_pareser.add_argument('-i','--include', type=str, nargs='+', default=[], choices=('pythoncode', 'searcher', 'file'), help='Include the extra interface, default: None, options: pythoncode, searcher, file')
helper_pareser.add_argument('-e','--extra-include', type=str, nargs='+', default=[], help='Include the extra interface, will find the interface in the specified python program path, format: path:interface:namespace')
helper_pareser.add_argument('--disable-authority', action='store_true', help='Disable authority, default: False', dest='disable_authority')

args = parser.parse_args()
if args.debug:
    __DEBUG__ = True

if not os.path.exists(args.config):
    logger.info("config.json Not Found. Use default config.")
    config_ = Config()
else:
    logger.info(f"{args.config} Found. Reading configure")
    config_ = Config.loadFromFile(args.config)

if config_["global.debug"]:
    __DEBUG__ = True

if __DEBUG__ == True:
    logger.setLevel(log.DEBUG)
    logger._cache = {}              # Issue: The logging cache will not be cleared when the logger level is changed
    logger.debug("Debug Mode Enabled")

# if args.disable_faiss:
#     config.varibles['disable_faiss'] = True

# Check the model
if args.model:
    match args.ai:
        case 'openaichat':
            config_['openaichat.model'] = args.model
        case 'bingai':
            config_['bingai.model'] = args.model
        case _:
            raise ValueError(f"Invalid AI: {args.ai}")

# After the initialization of the arguments and global configuration, we can now import the modules and do the real work
import json
from aicompleter import *
from aicompleter.implements import ConsoleInterface
from aicompleter.utils import ainput, aprint

__AI_map__ = {
    'openaichat': (ai.openai.Chater, {"config":config_['openaichat']}),
    'bingai': (ai.microsoft.BingAI, {"config":config_['bingai']}),
}
__Int_map__ = {
    'pythoncode': (implements.PythonCodeInterface, {}),
    'searcher': (implements.SearchInterface, {'config':config_['bingai']}),
    'file': (implements.system.FileInterface, {}),
}

handler_ = Handler(config_)
new_session:Session = None

has_loadHistory = False
def loadHistory() -> bool:
    global has_loadHistory
    path = args.history
    if not os.path.exists(path):
        if args.load_history:
            logger.warning(f"History file {path} not found. Ignore")
        return False
    if not args.load_history:
        # ask for user
        if not utils.is_enable(input("Load history?(Y/n) "), default=True):
            return
        # load history
        logger.info(f"Loading history from {path}")
        has_loadHistory = True
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        handler_.setstate(data['state'])
        global new_session
        new_session = handler_.loadSession(data['data'])
        return True
    else:
        return False

def saveHistory() -> bool:
    path = args.history
    if not (args.save_history or args.disable_history):
        # ask for user
        if not utils.is_enable(input("Save history?(Y/n) "), default=True):
            return False
        logger.info(f"Saving history to {path}")
        if not has_loadHistory:
            logger.warning("Overwrite the history file without loading it")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'state': handler_.getstate(),
                'data': new_session.json_data,
            }, f, indent=4)
        return True
    else:
        return False

async def main():
    global new_session
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
            await handler_.add_interface(ai_interface, con_interface)
            if loadHistory():
                # load success
                pass
            else:
                new_session = await handler_.new_session()

            usercontent = None
            await aprint("Please %s Your Conversation" % ("Start" if not has_loadHistory else "Continue"))
            while True:
                usercontent = await ainput(">>> ")
                ret:str = await new_session.asend(Message(
                    content = usercontent,
                    cmd = 'ask',
                    dest_interface=ai_interface,
                ))
                await aprint(ret)
        case 'helper':
            ai_name = args.ai
            if ai_name not in __AI_map__:
                logger.critical(f"AI {ai_name} not found.")
                return
            ai_cls, ai_param = __AI_map__[ai_name]
            ai_param["config"].setdefault(config_.global_)
            ai_ = ai_cls(**ai_param)

            ai_interface = (implements.logical.SelfStateExecutor if args.enable_agent else implements.logical.StateExecutor)(ai=ai_, namespace=ai_name)
            
            console_interface = ConsoleInterface()
            if not args.disable_authority:
                authority_interface = implements.AuthorInterface()
            # Authority should get the console interface permission
            graph = layer.InterfaceDiGraph()
            graph.add(ai_interface, console_interface)
            if not args.disable_authority:
                graph.add(authority_interface, console_interface)

            # Release the memory
            del ai_name, ai_cls, ai_param, ai_

            for interface_name in args.include:
                if interface_name not in __Int_map__:
                    logger.critical(f"Interface {interface_name} not found.")
                    return
                graph.add(ai_interface, __Int_map__[interface_name][0](**__Int_map__[interface_name][1]))

            for interface_name in args.extra_include:
                if ':' not in interface_name:
                    logger.critical(f"Invalid extra interface {interface_name}")
                    return
                path, interface, namespace = interface_name.split(':')
                try:
                    package = importlib.import_module(path)
                except ImportError as e:
                    logger.critical(f"ImportError: {e}")
                    return
                try:
                    _interface = getattr(package, interface)
                except AttributeError as e:
                    logger.critical(f"Interface Not Found: {e}")
                    return
                if not issubclass(_interface, Interface):
                    logger.critical(f"Invalid Interface: {interface}")
                    return
                
                _kwargs = {}
                if 'namespace' in _interface.__init__.__code__.co_varnames:
                    _kwargs['namespace'] = namespace
                if 'ai' in _interface.__init__.__code__.co_varnames:
                    # New AI class
                    _kwargs['ai'] = ai.ChatTransformer(name=namespace, config=config_[namespace])
                
                try:
                    the_interface = _interface(config=config_[namespace], **_kwargs)
                except Exception as e:
                    logger.critical(f"Exception when creating the interface instance {interface}: {e}")
                    return
                graph.add(ai_interface, the_interface)

            await graph.setup(handler_)

            if loadHistory():
                # load success
                pass
            else:
                new_session = await handler_.new_session()

            ret = await new_session.asend(Message(
                content = {
                    'content': 'Please %s Your Conversation' % ("Start" if not has_loadHistory else "Continue"),
                },
                cmd = 'ask',
                dest_interface=console_interface,
                session = new_session,
            ))
            await new_session.asend(Message(
                content = ret,
                cmd = 'agent',
                dest_interface=ai_interface,
                session = new_session,
            ))

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

loop = asyncio.new_event_loop()
loop.create_task(main())

# start the loop
utils.launch(
    loop=loop,
    logger=logger,
)

loop.create_task(handler_.close())
utils.launch(
    loop=loop,
    logger=logger,
)

saveHistory()

loop.close()
logger.debug("Loop Closed")
