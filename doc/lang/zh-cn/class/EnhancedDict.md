# Class EnhancedDict

增强型字典

## 元数据
|元数据|值|
|-|-|
|继承关系|继承至defaultdict|

## 特性
1. 缺省值: 在未找到对应Key的情况下, 默认返回一个新的EnhancedDict类
2. json格式: `value['a.b.c']` 完全等效于 `value['a']['b']['c']`
3. 锁特性: 创建会话修改数据需要获取异步锁, 直接修改不需要

## 成员

成员表:
|成员名|成员类型|成员原型|成员说明|
|-|-|-|-|
|`readonly`|property|`def readonly(self) -> bool`|字典是否只读|
|`set`|function|`def set(self, path:str, value:Any) -> None`|设置指定json路径的值|
|`get`|function|`def get(self, path:str, default:Any = None) -> Any`|获取指定json路径的值, 不存在则返回`EnhancedDict()`|
|`has`|function|`def has(self, path:str) -> bool`|指定路径是否存在|
|`require`|function|`def require(self, path:str) -> Any`|获取指定路径的值, 不存在则抛出`KeyError`异常|
|`setdefault`|function|`def setdefault(self, path:str, default:Any = None) -> Any`<br>`def setdefault(self, structdict:dict) -> Any`|设置指定路径的默认值, 或者设置默认的路径表|
|`update`|function|`def update(self, data:EnhancedDict) -> None`|用新的字典覆盖原有字典对应的值|
|`session`|function|`def session(self, locked:bool = True, save:bool = True) -> __Session`|开始一个新会话, 该操作回将字典上锁|
|`each`|function|`def each(self, func:Callable[[str, Any], Any], filter:Optional[Callable[[str, Any], bool]] = None) -> None`|对字典中每一个符合条件的子元素进行函数调用|
|`__contains__`|operator|`def __contains__(self, __key: str) -> bool`|判断对应的路径是否在该字典内|
|`__getitem__`|operator|`def __getitem__(self, __key: str) -> Any`|获取指定路径的值, 不存在则返回`EnhancedDict()`|

其它参考defaultclass
