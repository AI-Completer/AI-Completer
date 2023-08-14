import functools
from typing import Generic, Iterator, Optional, Self, TypeVar, overload

from . import *
from .utils.typeval import makeoverloadmethod

_T = TypeVar('_T')

class DiGraph(Generic[_T]):
    '''
    Directed graph.
    '''
    def __init__(self):
        self._src:dict[_T, set[_T]] = {}
    
    @overload
    def add(self, src:_T):
        ...

    @overload
    def add(self, src:_T, dest:_T):
        ...

    def add(self, src:_T, dest:Optional[_T] = None):
        '''
        Add a edge or add a node.
        '''
        if src not in self._src:
            self._src[src] = set()
        if dest != None:
            self._src[src].add(dest)
            if dest not in self._src:
                self._src[dest] = set()

    @overload
    def remove(self, src:_T) -> None:
        pass

    @overload
    def remove(self, src:_T, dest:_T) -> None:
        pass

    def remove(self, src:_T, dest:Optional[_T] = ...):
        '''Remove a edge'''
        if dest is ...:
            if src in self._src:
                self._src[src].remove(dest)
        else:
            if src in self._src:
                self._src.pop(src)
                for i in self._src:
                    if src in self._src[i]:
                        self._src[i].remove(src)

    def get(self, src:_T) -> set[_T]:
        '''Get the dests of a src'''
        return self._src.get(src, set())
    
    def __contains__(self, src:_T) -> bool:
        return src in self._src
    
    def __iter__(self) -> Iterator[_T]:
        return iter(self._src)
    
    def __len__(self) -> int:
        return len(self._src)
    
    def __bool__(self) -> bool:
        return bool(self._src)
    
    def __repr__(self) -> str:
        return f'DiGraph({self._src})'
    
    def __str__(self) -> str:
        return repr(self)
    
del _T

class InterfaceDiGraph(DiGraph[Interface]):
    '''
    Interface direct graph for calling commands.
    '''
    def __init__(self):
        super().__init__()
        self._structized = False

    @property
    def allinterfaces(self) -> list[Interface]:
        '''All interfaces'''
        return list(self._src.keys())

    def _update_groups(self):
        '''
        Update the groups of interfaces and commands
        '''
        _interfaces = self.allinterfaces
        for i in _interfaces:
            for cmd in i.commands:
                cmd.callable_groups.clear()
        _group_map = dict(zip(
            _interfaces,
            [f'DiGraph-{index}' for index in range(len(_interfaces))]
        ))
        for src in self._src:
            src._user.all_groups.add(_group_map[src])
            for dest in self._src[src]:
                dest.commands.each(lambda cmd: cmd.callable_groups.add(_group_map[src]))

    def unstructize(self):
        '''Unstructize the DiGraph'''
        if not self._structized:
            return
        for i in self.allinterfaces:
            for group in i._user.all_groups:
                if group.startswith('DiGraph-'):
                    i._user.all_groups.remove(group)
            for cmd in i.commands:
                for group in cmd.callable_groups:
                    if group.startswith('DiGraph-'):
                        cmd.callable_groups.remove(group)
        self._structized = False

    async def setup(self, handler:Handler):
        '''Setup the tree'''
        for i in handler.interfaces:
            handler.rm_interface(i)
        await handler.add_interface(*self.allinterfaces)
        self._update_groups()
        handler.reload()

class CommandCallMap:
    '''
    map for command call permission management.
    '''
    def __init__(self):
        self._src:dict[tuple[Interface, Interface], set(str)] = {}
        '''
        :param tuple[Interface, Interface] src: (src, dest)
        :param str dest: dest command name
        '''


    @overload
    def add(self, node: Interface):
        ...

    @overload
    def add(self, src:Interface, dest:Interface):
        ...

    @overload
    def add(self, src:Interface, dest:Interface, dest_cmd:str):
        ...

    def add(self, src:Interface, dest:Optional[Interface] = None, dest_cmd:Optional[str] = None):
        '''
        Add a node or an edge

        If dest is None, this command will add a node.
        If dest_cmd is None, all commands in dest will be callable.
        '''
        if (src, dest) not in self._src:
            self._src[(src, dest)] = set()
        if dest != None:
            if dest_cmd is None:
                for cmd in dest.commands:
                    self._src[(src, dest)].add(cmd.cmd)
            else:
                self._src[(src, dest)].add(dest_cmd)

    @overload
    def remove(self, src:Interface) -> None:
        pass

    @overload
    def remove(self, src:Interface, dest:Interface) -> None:
        pass

    @overload
    def remove(self, src:Interface, dest:Interface, dest_cmd:str) -> None:
        pass

    @makeoverloadmethod
    def remove(self, *args):
        raise TypeError(f'Invalid args: {args}')
    
    @remove.register_auto
    def _(self, src:Interface):
        '''Remove a edge'''
        for i in self._src:
            if i[0] == src:
                self._src.pop(i)

    @remove.register_auto
    def _(self, src:Interface, dest:Interface):
        '''Remove a edge'''
        if (src, dest) in self._src:
            self._src.pop((src, dest))

    @remove.register_auto
    def _(self, src:Interface, dest:Interface, dest_cmd:str):
        '''Remove a edge'''
        if (src, dest) in self._src:
            self._src[(src, dest)].remove(dest_cmd)

    def get(self, src:Interface, dest:Interface) -> set[str]:
        '''Get the dests of a src'''
        return self._src.get((src, dest), set())
    
    def __contains__(self, src:Interface) -> bool:
        for i in self._src:
            if i[0] == src:
                return True
        return False
    
    def __iter__(self) -> Iterator[tuple[Interface, Interface]]:
        return iter(self._src)
    
    def __len__(self) -> int:
        return len(self._src)
    
    def __bool__(self) -> bool:
        return bool(self._src)
    
    def __repr__(self) -> str:
        return f'CommandCallMap({self._src})'
    
    def __str__(self) -> str:
        return repr(self)
    
    def _update_group(self):
        '''
        Update the groups of interfaces and commands
        '''
        _interfaces:set[Interface] = set()
        for i in self._src:
            _interfaces.add(i[0])
            _interfaces.add(i[1])
        _interfaces = list(_interfaces)
        for i in _interfaces:
            for cmd in i.commands:
                cmd.callable_groups.clear()
        _group_map = dict(zip(
            _interfaces,
            [f'CommandCallMap-{index}' for index in range(len(_interfaces))]
        ))
        for src in _interfaces:
            src._user.all_groups.add(_group_map[src])
            for dest in _interfaces:
                for cmd in self.get(src, dest):
                    dest.commands[cmd].callable_groups.add(_group_map[src])

    def unstructize(self):
        '''Unstructize the DiGraph'''
        if not self:
            return
        for i in self:
            for group in i[0]._user.all_groups:
                if group.startswith('CommandCallMap-'):
                    i[0]._user.all_groups.remove(group)
            for cmd in i[0].commands:
                for group in cmd.callable_groups:
                    if group.startswith('CommandCallMap-'):
                        cmd.callable_groups.remove(group)
        self._structized = False

    async def setup(self, handler:Handler):
        '''Setup the tree'''
        for i in handler.interfaces:
            handler.rm_interface(i)
        _interfaces:set[Interface] = set()
        for i in self._src:
            _interfaces.add(i[0])
            _interfaces.add(i[1])
        await handler.add_interface(*_interfaces)
        self._update_group()
        handler.reload()

