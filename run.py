#!/usr/bin/python3
# -*- coding: utf-8 -*-

# This module will check the config and some other things, and then pass the config to the main program

import os
import runpy
import sys
import json
from typing import Optional

if sys.version_info < (3, 11):
    raise RuntimeError('This program requires python 3.11 or higher.')

from aicompleter.log import Logger, getLogger
from aicompleter import utils
logger = getLogger('startup')

def require_input(prompt:Optional[str] = None, default:Optional[str] = ...) -> str:
    '''
    Require input from the user
    '''
    ret = None
    while not ret:
        if prompt:
            print(prompt)
        ret = input('>>> ')
        if not ret:
            if default != ...:
                print("Using default value: " + default)
                return default
            else:
                print('Value required.')
    return ret

try:

    # Check if the config file exists
    if not os.path.exists('config.json'):
        logger.info('Config file not found, creating...')
        config = {
            'global':{
                'openai':{
                    'api_key': '',
                    'api_url': '',
                },
                "debug": False,
            },
            'openaichat':{
                'model': 'gpt-3.5-turbo',
            },
            'bingai':{
                'model': 'balanced',
            }
        }
        # Require OpenAI API key
        config['global']['openai']['api_key'] = require_input('OpenAI API key: ')
        config['global']['openai']['api_url'] = require_input('OpenAI API URL (default to https://api.openai.com/v1): ', 'https://api.openai.com/v1')
        # Require OpenAI model
        config['openaichat']['model'] = require_input('OpenAI model (default to gpt-3.5-turbo): ', 'gpt-3.5-turbo')
        # Require Bing AI model
        config['bingai']['model'] = require_input('Bing AI model (default to balanced): ', 'balanced')
        # Require proxy
        proxy = require_input('Proxy (default to None): ', None)
        if proxy:
            config['global']['proxy'] = proxy
        # Require debug
        while True:
            try:
                config['global']['debug'] =utils.is_enable(require_input('Debug (default to False): ', False))
                break
            except ValueError as e:
                print(e.args[0])
        # Write config
        logger.info('Writing config...')
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
    else:
        logger.info('Config file found')
    
except KeyboardInterrupt:
    logger.info('KeyboardInterrupt, exiting...')
    sys.exit(1)
except Exception as e:
    logger.critical('Unexception:' + str(e))
    sys.exit(2)

# Add default system arguments if not exists
oldargv = sys.argv
if len(sys.argv) == 1:
    # Add default arguments
    sys.argv = ['aicompleter', '--config', 'config.json', 'helper', '--enable-agent', '--include','pythoncode','--include','searcher']
    # TODO: Get available ai model

elif os.path.isfile(sys.argv[1]):
    # Run the file, instead of the helper
    # With the other parameters
    executor = sys.argv[0]
    logger.info('Running file: ' + sys.argv[1])
    os.execvp(executor, sys.argv)
    sys.exit(0)

# Launch the main program
runpy.run_module('aicompleter', run_name='__main__', alter_sys=True)

# Restore sys.argv
sys.argv = oldargv
