import json
import attr

@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Role:
    name:str = ""
    id:str = ""
    attrs:dict = {}

User=Role(name="user")
Admin=Role(name="admin")
Guest=Role(name="guest")
Bot=Role(name="bot")
System=Role(name="system")
Agent=Role(name="agent")

roles:dict={
    "user":User,
    "admin":Admin,
    "guest":Guest,
    "bot":Bot,
    "system":System,
    "agent":Agent,
}
