from __future__ import annotations
import json
import logging
from autodone.session.base import MultiContent
import role
import time

class Sentence:
    '''Sentence In Conversation'''
    def __init__(self, content:MultiContent, role:role.Role, time:float|None = None) -> None:
        self.content:MultiContent = content
        self.role:role.Role = role
        self.time:float = time if time is not None else time.time()
    
    def to_json(self) -> str:
        '''Translate to JSON string'''
        return json.dumps({
            "content":self.content.text,
            "role":self.role.to_json(),
            "time":self.time
        })
    
    @staticmethod
    def from_json(json_str:str) -> Sentence:
        '''Translate from JSON string'''
        json_dict = json.loads(json_str)
        return Sentence(
            content=MultiContent(json_dict["content"]),
            role=role.Role.from_json(json_dict["role"]),
            time=json_dict["time"]
        )

class Conversation:
    '''Conversation'''
    def __init__(self) -> None:
        self.roles:list[role.Role] = []
        '''Role list'''
        self.sentences:list[Sentence] = []
        '''Sentence list'''
        self.extra:dict = {}
        '''Extra information'''

    def add_sentence(self, sentence:Sentence) -> None:
        '''Add a sentence to conversation'''
        self.sentences.append(sentence)
        if sentence.role not in self.roles:
            self.roles.append(sentence.role)

    def to_json(self) -> str:
        '''Translate to JSON string'''
        return json.dumps({
            "roles":[role.to_json() for role in self.roles],
            "sentences":[sentence.to_json() for sentence in self.sentences],
            "extra":self.extra
        })
    
    @staticmethod
    def from_json(json_str:str) -> Conversation:
        '''Translate from JSON string'''
        json_dict = json.loads(json_str)
        conversation = Conversation()
        conversation.roles = [role.Role.from_json(role_json) for role_json in json_dict["roles"]]
        conversation.sentences = [Sentence.from_json(sentence_json) for sentence_json in json_dict["sentences"]]
        conversation.extra = json_dict["extra"]
        return conversation

    