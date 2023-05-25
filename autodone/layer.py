from typing import Iterator, Self
from . import *

class DiGraph:
    '''
    Interface direct graph for calling commands.
    '''
    def __init__(self):
        self._src:dict[Interface, set[Interface]] = {}
        self._structized = False

    def add(self, src:Interface, dest:Interface):
        '''Add a edge'''
        if src not in self._src:
            self._src[src] = set()
        self._src[src].add(dest)
        if dest not in self._src:
            self._src[dest] = set()

    def remove(self, src:Interface, dest:Interface):
        '''Remove a edge'''
        if src in self._src:
            self._src[src].remove(dest)
    
    def get(self, src:Interface) -> set[Interface]:
        '''Get the dests of a src'''
        return self._src.get(src, set())
    
    def rm_interface(self, interface:Interface):
        '''Remove an interface'''
        if interface in self._src:
            del self._src[interface]
        for i in self._src.values():
            if interface in i:
                i.remove(interface)

    def __contains__(self, interface:Interface) -> bool:
        return interface in self._src
    
    def __iter__(self) -> Iterator[Interface]:
        return iter(self._src)

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
        