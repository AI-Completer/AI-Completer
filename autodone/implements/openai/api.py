import asyncio
import json
from re import L
from typing import Any, Iterable, Literal, Optional, TypeVar

import aiohttp
import attr

Model = TypeVar('Model', str)

@attr.s(auto_attribs=True)
class CommonParameters:
    '''
    Common parameters for OpenAI API
    '''
    model:Model = 'davinci'
    '''
    The model to use for completion. Defaults to davinci. See the [guide](https://beta.openai.com/docs/api-reference/completions/create#completion.create) for more information.
    '''
    max_tokens:Optional[int] = None
    '''
    The maximum number of tokens to generate. Requests can use up to 2048 tokens shared between prompt and completion. (One token is roughly 4 characters for normal English text.) Defaults to 16.
    On chat completion, the default is inf.
    '''
    temperature:Optional[float] = None
    '''
    What sampling temperature to use. Higher values means the model will take more risks. Try 0.9 for more creative applications, and 0 (argmax sampling) for ones with a well-defined answer. Defaults to 1.
    '''
    top_p:Optional[float] = None
    '''
    An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered. Defaults to 1.
    '''
    n:Optional[int] = None
    '''
    How many completions to generate for each prompt. Defaults to 1.
    '''
    stream:Optional[bool] = None
    '''
    Whether to stream back partial progress. If set, tokens will be sent as data-only server-sent events as they become available, with the stream terminated by a data: [DONE] message. Defaults to false.
    '''
    stop:Optional[str] = None
    '''
    One or more (up to 4) sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence.
    '''
    presence_penalty:Optional[float] = None
    '''
    What sampling penalty to apply to each token not yet generated. Defaults to 0.
    '''
    frequency_penalty:Optional[float] = None
    '''
    What sampling penalty to apply to the frequency of words in the generated text. Defaults to 0.
    '''
    logit_bias:Optional[dict] = None
    '''
    A map of tokens to their logit bias that may be used to tweak the model's output. Entries are strings that may be up to 32 characters long, with alphanumeric characters and hyphens only. Defaults to {}.
    '''
    user:Optional[str] = None
    '''
    The user ID to impersonate. Must be a string, and the current user must have permission to impersonate the given user ID. For more information on how to use this parameter, see the [API guide](https://beta.openai.com/docs/api-reference/authorizations/create#authorizations.create).
    '''

    def to_json(self) -> dict:
        '''
        Convert to json
        '''
        return attr.asdict(self, filter=lambda attr, value: value is not None)
    
    def from_json(self, data:dict) -> None:
        '''
        Convert from json
        '''
        self.__dict__.update(data)

@attr.s(auto_attribs=True)
class CompletionParameters(CommonParameters):
    '''
    Completion parameters for OpenAI API
    '''
    prompt:str
    '''
    The prompt(s) to generate completions for. The API max length is 2048 tokens. One token is roughly 4 characters for normal English text.
    '''
    suffix:Optional[str] = None
    '''
    A special suffix to append to the prompt. This can be useful to add a special token at the end for delimiting a prompt. For example, if your prompt is "Once upon a time", you may want to add a stop token at the end: "Once upon a time" [STOP]
    '''
    logprobs:Optional[int] = None
    '''
    Include the log probabilities on the logprobs most likely tokens, as well the chosen tokens. For example, if logprobs is 10, the API will return a list of the 10 most likely tokens. If logprobs is supplied, the API will always return the logprob of the sampled token, so there may be up to logprobs+1 elements in the response.
    '''
    echo:Optional[bool] = None
    '''
    Echo back the prompt in addition to the completion, defaults to false.
    '''
    best_of:Optional[int] = None
    '''
    Generates best_of completions server-side and returns the "best" (the one with the lowest log probability per token). Results cannot be streamed.
    '''

@attr.s(auto_attribs=True)
class Message:
    '''
    Message for OpenAI API
    '''
    role:Literal['system', 'user', 'agent'] = 'user'
    '''
    The role of the messager
    '''
    content:str
    '''
    The content of the message
    '''
    name:Optional[str] = None
    '''
    The name of the messager
    '''

    def to_json(self) -> dict:
        '''
        Convert to json
        '''
        return attr.asdict(self, filter=lambda attr, value: value is not None)

    def __str__(self):
        return "{%s}" % f'role: {self.role}, content: {self.content}, name: {self.name}'
    
    def __repr__(self):
        return self.__str__()

@attr.s(auto_attribs=True)
class ChatParameters(CommonParameters):
    '''
    Chat parameters for OpenAI API
    '''
    messages:list[Message] = []
    '''
    A list of messagers
    '''

BASE_URL:str = 'https://api.openai.com/v1/'
COMPLETIONS_URL:str = f'{BASE_URL}completions'
CHAT_URL:str = f'{BASE_URL}chat/completions'

class EnterPoint:
    '''
    Enterpoint for OpenAI API
    '''
    def __init__(self, api_key:str):
        self.api_key = api_key
        self.session = aiohttp.ClientSession()

    async def _request(self, url:str, parameters:CommonParameters) -> dict:
        with self.session.post(url, data=parameters.to_json(), headers={
            'Content-Type': 'application/json',
            'Authorization':f"Bearer {self.api_key}",
        }) as res:
            return await res.json()

    async def completions(self, parameters:CompletionParameters) -> dict:
        '''
        Call OpenAI completions API
        '''
        return await self._request(COMPLETIONS_URL, parameters)
    
    async def chat(self, parameters:ChatParameters) -> dict:
        '''
        Call OpenAI chat API
        '''
        return await self._request(CHAT_URL, parameters)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()


