'''
Language module

This module is only used to store the language data which will be used in the `implements` modules.
If you want to store your own language data, just dynamically add a new key to the `DICT` dict.
'''

DICT = {
    'zh-cn':{
        'greeting':'你好',
        'greeting_reply':'你好, 有什么可以帮助你的吗?',
        'start_task':'请开始你的任务',
    },
    'en-us':{
        'greeting':'Hello',
        'greeting_reply':'Hello, what can I do for you?',
        'start_task':'Please start your task',
    },
}

