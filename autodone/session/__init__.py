'''
This package contains the Session class, which is the main class of the
autodone package. It is used to store the state of the session, including
the HTTP session, the conversation, the roles, and the extra information.
'''
from session import Session
from role import Role,roles
from conversation import Sentence, Conversation
from base import MultiContent,Content,Text,Image,Audio,Session,Message
