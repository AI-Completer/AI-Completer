from typing import Generic, Iterator, Optional, Self, TypeVar, overload
from . import *

_T = TypeVar('_T')

class DiGraph(Generic[_T]):
    '''
    Directed graph.
    '''
    def __init__(self):
        self._src:dict[_T, set[_T]] = {}
        
    def add(self, src:_T, dest:_T):
        '''Add a edge'''
        if src not in self._src:
            self._src[src] = set()
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
        handler._interfaces.clear()
        await handler.add_interface(*self.allinterfaces)
        self._update_groups()
        handler.reload()

class CommandCallMap:
    '''
    map for command call permission management.
    '''
    def __init__(self):
        self._src:dict[tuple[Interface, Interface], str] = {}
        '''
        :param tuple[Interface, Interface] src: (src, dest)
        :param str dest: dest command name
        '''

    
