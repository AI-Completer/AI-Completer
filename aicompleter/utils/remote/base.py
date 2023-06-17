import asyncio
from typing import Any, Callable, Coroutine, Optional, Self
from . import asocket
import uuid
import json
import pickle
from . import error
import attr

PICKLE_DEFAULT_PROTOCAL = 5

@attr.s(auto_attribs=True)
class RemoteEnvironment:
    '''
    Remote environment.
    '''
    id: uuid.UUID = attr.ib(factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID))
    'Remote environment id'
    varible_map: dict[str, object] = attr.ib(factory=dict, validator=attr.validators.instance_of(dict))
    'Varible map'

class RemoteControler:
    '''
    Remote controler.
    To modify the variable and execute the command in the remote process.
    '''
    def __init__(self, connection:asocket.jsonconnection):
        self._connection = connection
        self._closed = False
        self._recv__task = asyncio.create_task(self._on_recv())
        self.on_error:Callable[[Exception, RemoteEnvironment], Coroutine[None, None, Any]] = lambda error, env: asyncio.create_task()
        self.environs:dict[uuid.UUID, RemoteEnvironment] = {}

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

    async def execute(self, envid:uuid.UUID ,pycode: str):
        '''
        Call a function.
        '''
        ret = await self._connection.request({
            'type': 'execute',
            'envid': envid,
            'code': pycode,
        })
        if ret['type'] == 'error':
            raise error.RemoteError(pickle.loads(ret['error']))
        return pickle.loads(ret['return'])
    
    async def pickle(self, envid:uuid.UUID, remote_name:str) -> object:
        '''
        Pickle a object.
        '''
        ret = await self._connection.request({
            'type': 'pickle',
            'envid': envid,
            'object': remote_name,
        })
        if ret['type'] == 'error':
            raise RuntimeError(ret['error'])
        return pickle.loads(ret['return'])

    async def _on_execute(self, data:dict):
        '''
        Call a function.
        '''
        if 'code' not in data:
            raise error.ProtocalError('No code')
        return eval(data['code'], self.environs[data['envid']].varible_map)
    
    async def _on_pickle(self, data:dict):
        '''
        Pickle a object.
        '''
        if 'object' not in data:
            raise error.ProtocalError('No object')
        def get_object(name:str, _parent:object = None) -> object:
            if 'envid' not in data:
                raise error.ProtocalError('No envid')
            if '.' in name:
                name, subname = name.split('.', 1)
                return get_object(subname, getattr(_parent, name))
            if _parent is None:
                return self.environs[data['envid']][name]
            return getattr(_parent, name)
        return pickle.dumps(get_object(data['object']), PICKLE_DEFAULT_PROTOCAL)
    
    async def _on_call(self, data:dict):
        '''
        On call function.
        {"path": "path.to.function", "args": pickle.dumps(args), "kwargs": pickle.dumps(kwargs), "envid": envid}
        return: {'async': True/False, 'return': pickle.dumps(return)}
        '''
        def _get_func(path:str, _parent:object = None):
            if '.' in path:
                name, subname = path.split('.', 1)
                return _get_func(subname, getattr(_parent, name))
            if _parent is None:
                return self.environs[data['envid']][path]
            return getattr(_parent, path)
        func = _get_func(data['path'])
        if not callable(func):
            raise error.ProtocalError(f"{data['path']} is not callable")
        args = pickle.loads(data['args'])
        kwargs = pickle.loads(data['kwargs'])
        if asyncio.iscoroutinefunction(func):
            return {
                'async': True,
                'return': pickle.dumps(await func(*args, **kwargs), PICKLE_DEFAULT_PROTOCAL)
            }
        return {
            'async': False,
            'return': pickle.dumps(func(*args, **kwargs), PICKLE_DEFAULT_PROTOCAL)
        }
    
    async def call(self, envid:uuid.UUID, path:str, args:tuple, kwargs:dict):
        '''
        Call a function.
        '''
        ret = await self._connection.request({
            'type': 'call',
            'envid': envid,
            'path': path,
            'args': pickle.dumps(args, PICKLE_DEFAULT_PROTOCAL),
            'kwargs': pickle.dumps(kwargs, PICKLE_DEFAULT_PROTOCAL),
        })
        if ret['type'] == 'error':
            raise error.RemoteError(pickle.loads(ret['error']))
        if ret['async']:
            return await pickle.loads(ret['return'])
        return pickle.loads(ret['return'])
    
    async def raw_call(self, envid:uuid.UUID, path:str, args:tuple, kwargs:dict):
        '''
        Call a function.
        '''
        ret = await self._connection.request({
            'type': 'call',
            'envid': envid,
            'path': path,
            'args': pickle.dumps(args, PICKLE_DEFAULT_PROTOCAL),
            'kwargs': pickle.dumps(kwargs, PICKLE_DEFAULT_PROTOCAL),
        })
        if ret['type'] == 'error':
            raise error.RemoteError(pickle.loads(ret['error']))
        return ret
    
    async def _on_recv(self):
        '''
        Receive data from the connection.
        '''
        while not self._closed:
            await asyncio.get_event_loop().create_task()
            async with self._connection.conversation():
                if self._connection.at_eof():
                    continue
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
        self.__controler = controler
        self.__name = name
        self.__parent = parent
        self.__raw_value:Optional[object] = None
        self.__subattrs:dict[str, Self] = {}
        self.__submethods:dict[str, Callable[..., Coroutine[None, None, Any]]] = {}
        self.__subclasses:dict[str, Self] = {}

    def __get_remote_name__(self) -> str:
        '''
        Get the name of the remote attribute.
        '''
        if self.__parent is None:
            return self.__name
        return f"{self.__parent.__get_remote_name__()}.{self.__name}"
    
    async def __aload__(self, *args, **kwargs):
        '''
        Load the varible from the remote
        '''
        if self.__raw_value is not None:
            return
        if self._parent:
            self.__raw_value = getattr(self.__parent.__raw_value, self.__name)
        else:
            self.__raw_value = await self.__controler.pickle(self.__name)
        if isinstance(self.__raw_value, type):
            for name in dir(self.__raw_value):
                if name in self.__subclasses:
                    continue
                self.__subclasses[name] = RemoteAttribute(self.__controler, name, self)
        else:
            for name in dir(self.__raw_value):
                if name in self.__submethods:
                    continue
                if callable(getattr(self.__raw_value, name)):
                    self.__submethods[name] = RemoteAttribute(self.__controler, name, self)
                else:
                    self.__subattrs[name] = RemoteAttribute(self.__controler, name, self)
    
    def __getattribute__(self, name:str) -> Self:
        '''
        Get a attribute.
        '''
        if name in ['__controler', '__name', '__parent', '__raw_value', '__subattrs', '__submethods', '__subclasses']:
            return super().__getattribute__(name)
        if name in self.__subattrs:
            return self.__subattrs[name]
        if name in self.__submethods:
            return self.__submethods[name]
        if name in self.__subclasses:
            return self.__subclasses[name]
        raise AttributeError(f"Unknown attribute: {name}")
    
    def __call__(self, *args: Any, **kwds: Any):
        '''
        Call a function.
        '''
        try:
            ret = asyncio.get_event_loop().run_until_complete(self.__controler.raw_call(self.__get_remote_name__(), args, kwds))
        except error.RemoteError as e:
            e.reraise()
        if ret['async']:
            async def _asy_return():
                return pickle.loads(ret['return'])
            return _asy_return()
        return pickle.loads(ret['return'])

class RemoteAttributor:
    '''
    Remote attribute control.
    '''
    def __init__(self, controler:RemoteControler):
        self.controler = controler

