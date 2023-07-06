# Class Message

消息体

## 元数据
|元数据|值|
|-|-|
|继承关系|继承至object|
|修饰|attr|

## 特性
1. 结构体: 无任何实际效用代码

## 成员
|成员名|成员类型|成员原型|成员说明|
|-|-|-|-|
|`content`|attribute|`content:MultiContent = attr.ib(factory=MultiContent, converter=MultiContent)`|消息内容|
|`session`|attribute|`session:Session = attr.ib(validator=attr.validators.instance_of(Session))`|消息所处的会话|
|`id`|attribute|`id:uuid.UUID = attr.ib(factory=uuid.uuid4, validator=attr.validators.instance_of(uuid.UUID))`|消息id|
|`data`|attribute|`data:EnhancedDict = attr.ib(factory=EnhancedDict, converter=EnhancedDict, alias='extra')`|消息的额外数据(deprecated)|
|`last_message`|attribute|`last_message: Optional[Message] = None`|引发此消息的上一条消息, 可选|
|`cmd`|attribute|`cmd:str`|调用的命令|
|`src_interface`|attribute|`src_interface:Optional[Interface] = None`|源接口,可选,如果为None,将不检查权限|
|`dest_interface`|attribute|`dest_interface:Optional[Interface] = None`|目标接口,可选|
|`status`|property|`def status(self) -> MessageStatus`|消息当前状态|
