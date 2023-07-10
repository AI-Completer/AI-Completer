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

def try_parse_bool(value:str) -> bool:
    '''
    Try to parse a string to bool
    '''
    if value.lower() in ('true', 'yes', '1' , 'y', 't'):
        return True
    elif value.lower() in ('false', 'no', '0', 'n', 'f'):
        return False
    else:
        raise ValueError(f'Invalid bool value {value}')

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
                config['global']['debug'] = try_parse_bool(require_input('Debug (default to False): ', 'False'))
                break
            except ValueError as e:
                print(e.args[0])
        # Write config
        logger.info('Writing config...')
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
    else:
        logger.info('Config file found, loading...')
        with open('config.json', 'r') as f:
            config = json.load(f)
    
except KeyboardInterrupt:
    logger.info('KeyboardInterrupt, exiting...')
    sys.exit(1)
except Exception as e:
    logger.critical('Unexception:' + str(e))
    sys.exit(2)

# Launch the main program
runpy.run_module('aicompleter', run_name='__main__', alter_sys=True)
