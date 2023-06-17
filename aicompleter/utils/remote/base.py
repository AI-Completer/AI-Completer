import asyncio
from typing import Any, Callable, Coroutine, Optional, Self
from . import asocket
import uuid
import json
import pickle

PICKLE_DEFAULT_PROTOCAL = 5

class RemoteControler:
    '''
    Remote controler.
    To modify the variable and execute the command in the remote process.
    '''
    def __init__(self, connection:asocket.jsonconnection):
        self._connection = connection
        self._closed = False
        self._recv__task = asyncio.create_task(self._on_recv())
        self.on_error:Callable[[str], Coroutine[None, None, Any]] = lambda error: None

    async def close(self):
        '''Close the connection.'''
        if self._closed:
            return
        self._closed = True
        await self._connection.close()

    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def execute(self, pycode: str):
        '''
        Call a function.
        '''
        await self._connection.send({
            'type': 'execute',
            'code': pycode,
        })
        ret = await self._connection.recv()
        if ret['type'] == 'error':
            raise RuntimeError(ret['error'])
        return ret['return']
    
    async def pickle(self, remote_name:str) -> object:
        '''
        Pickle a object.
        '''
        await self._connection.send({
            'type': 'pickle',
            'object': remote_name,
        })
        ret = await self._connection.recv()
        if ret['type'] == 'error':
            raise RuntimeError(ret['error'])
        return pickle.loads(ret['return'], encoding='bytes')

    async def _on_execute(self, data:dict):
        '''
        Call a function.
        '''
        if 'code' not in data:
            raise ValueError('No code')
        try:
            ret = eval(data['code'], globals(), locals())
        except Exception as e:
            raise ValueError(f"Error when executing: {e}")
        return ret
    
    async def _on_pickle(self, data:dict):
        '''
        Pickle a object.
        '''
        if 'object' not in data:
            raise ValueError('No object')
        try:
            return pickle.dumps(data['object'], PICKLE_DEFAULT_PROTOCAL)
        except Exception as e:
            raise ValueError(f"Error when pickling: {e}")

    async def _on_recv(self):
        '''
        Receive data from the connection.
        '''
        while not self._closed:
            data = await self._connection.recv()
            try:
                if data['type'] == 'recv':
                    raise NotImplementedError()
                elif data['type'] == 'error':
                    await self.on_error(pickle.loads(data['error'], encoding='bytes'))
                    continue
                # execute the type
                if f"_on_{data['type']}" in dir(self):
                    ret = await getattr(self, f"_on_{data['type']}")(data)
                    await self._connection.send({
                        'type': 'return',
                        'return': ret,
                    })
                else:
                    raise ValueError(f"Unknown type: {data['type']}")
            except Exception as e:
                await self._connection.send({
                    'type': 'error',
                    'error': pickle.dumps(e, PICKLE_DEFAULT_PROTOCAL)
                })

class RemoteAttribute:
    '''
    Remote attribute.
    '''
    def __init__(self, controler:RemoteControler, name:str, parent:Optional[Self] = None):
        self.controler = controler
        self._name = name
        self._parent = parent
        self._raw_value:Optional[object] = None
        self._subattrs:dict[str, Self] = {}
        self._submethods:dict[str, Callable[..., Coroutine[None, None, Any]]] = {}
        self._subclasses:dict[str, Self] = {}

    def __get_remote_name__(self) -> str:
        '''
        Get the name of the remote attribute.
        '''
        if self._parent is None:
            return self._name
        return f"{self._parent.__get_remote_name__()}.{self._name}"
    
    async def __aload__(self, *args, **kwargs):
        '''
        Load the varible from the remote
        '''
        if self._raw_value is not None:
            return
        

    def __getchild__(self, name:str) -> Self:
        '''
        Get a child attribute.
        '''
        if name not in self._subattrs:
            self._subattrs[name] = RemoteAttribute(self.controler, name, self)
        return self._subattrs[name]
    


class RemoteAttributor:
    '''
    Remote attribute control.
    '''
    def __init__(self, controler:RemoteControler):
        self.controler = controler

