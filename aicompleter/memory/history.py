'''
Read and save the memory to the disk
'''
import json
import os
from typing import Iterator
from .base import Memory, MemoryItem, Query

class HistoryFile:
    '''
    Memory History File
    Now for file use.
    '''
    def __init__(self, path:str):
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, 'w') as f:
                f.write('[]')
        self.file = open(self.path, 'rw')
        self.file.seek(0)

    def readall(self) -> Iterator[MemoryItem]:
        '''
        Read all the history
        '''
        data = json.load(self.file)
        self.file.seek(0)
        for item in data:
            yield MemoryItem.from_dict(item)

    def writeall(self, memory:Memory):
        '''
        Write all the memory
        '''
        json.dump([i.to_dict() for i in memory.all()],self.file)
        self.file.seek(0)

    def append(self, item:MemoryItem):
        '''
        Append a history item
        '''
        data:list = json.load(self.file)
        self.file.seek(0)
        data.append(item.to_dict())
        json.dump(data, self.file)
    
    def clear(self):
        '''
        Clear the history
        '''
        self.file.seek(0)
        self.file.truncate()
        self.file.write('[]')
        self.file.seek(0)

    def save(self):
        '''
        Save the history
        '''
        self.file.flush()

    def __del__(self):
        self.file.close()

