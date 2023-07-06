# Class Session

会话类, 包含所有已知的会话信息

## 元数据
|元数据|值|
|-|-|
|继承关系|继承自object|

## 特性
1. 数据表: 无实际作用的函数

## 成员
|成员名|成员类型|成员原型|成员说明|
|-|-|-|-|
|`create_time`|varible|`self.create_time:float=time.time()`|创建该类的时间|
|`history`|varible|`self.history:list[Message] = []`|消息历史|
|`in_handler`|varible|`self.in_handler:Handler = handler`|会话所在的处理器|
|`config`|varible|`self.config:Config = Config()`|会话配置|
|`data`|varible|`self.data:EnhancedDict = EnhancedDict()`|会话数据|
|`logger`|varible|`self.logger:log.Logger=log.Logger('session')`|会话日志器|
|`id`|property|`def id(self) -> uuid.UUID`|会话ID|
|`extra`|property(alias)|`def extra(self) -> EnhancedDict`|会话数据|
|`asend`|function|`def asend(self, message:Message)`|协程发送消息|
|`send`|function|`def send(self, message:Message)`|发送消息|
|`close`|function|`async def close(self)`|关闭会话|
