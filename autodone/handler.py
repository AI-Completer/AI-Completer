'''
Handler between the interfaces
'''
from typing import overload
from autodone.interface.base import Interface, Command, Role
import session
import asyncio
import uuid
import error

class MessageQueue(asyncio.Queue[session.Message]):
    '''Message Queue'''
    def __init__(self, id:uuid.UUID = uuid.uuid4()):
        self.id:uuid.UUID = id

class Handler:
    '''
    Handler for AutoDone-AI
    The handler will transfer various information between Interfaces, 
    enabling interaction among person, AI and system.
    '''
    def __init__(self) -> None:
        self._interfaces:set[Interface] = set()

    def add_interface(self, interface:Interface) -> None:
        '''Add interface to the handler'''
        if interface in self._interfaces:
            raise error.Existed(interface, handler=self)
        self._interfaces.add(interface)

    @overload
    def rm_interface(self, interface:Interface) -> None:
        pass

    @overload
    def rm_interface(self, id:uuid.UUID) -> None:
        pass

    def rm_interface(self, param:Interface or uuid.UUID) -> None:
        '''Remove interface from the handler'''
        if isinstance(param, Interface):
            if param not in self._interfaces:
                raise error.NotFound(param, handler=self)
            self._interfaces.remove(param)
        elif isinstance(param, uuid.UUID):
            for i in self._interfaces:
                if i.id == param:
                    self._interfaces.remove(i)
                    return
            raise error.NotFound(param, handler=self)
        else:
            raise TypeError(f"Expected type Interface or uuid.UUID, got {type(param)}")
        
    def get_interface(self, id:uuid.UUID) -> Interface:
        '''Get interface by id'''
        for i in self._interfaces:
            if i.id == id:
                return i
        raise error.NotFound(id, handler=self)
    
    def get_interfaces(self, role:Role) -> set[Interface]:
        '''Get interfaces by role'''
        ret = set()
        for i in self._interfaces:
            if i.role == role:
                ret.add(i)
        return ret
    
    
    
    

        


