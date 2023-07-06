# Class Config

配置类, 用于管理配置项

## 元数据
|元数据|值|
|-|-|
|继承关系|继承自[EnhancedDict](EnhancedDict.md)|

## 特性
1. 限定类型: 只有指定类型的值被允许: str, int, float, bool, NoneType

其它参见[EnhancedDict-特性](EnhancedDict.md#特性)

## 成员

成员表:
|成员名|成员类型|成员原型|成员说明|
|-|-|-|-|
|`ALLOWED_VALUE_TYPE`|constants|`ALLOWED_VALUE_TYPE = (str, int, float, bool, type(None))`|记载允许的所有常量|
|`loadFromFile`|function|`def loadFromFile(path:str) -> Config`|从文件中加载配置|
|`require`|function|`def require(self, path: str) -> Any`|重写KeyError错误，参见[EnhancedDict](EnhancedDict.md#成员)|
|`save`|function|`def save(self, path:str) -> None`|保存配置到文件|
|`global_`|property|`def global_(self) -> Config`|全局配置,指`self['global']`|

其它参见[EnhancedDict](EnhancedDict.md#成员)

## 格式

Config应遵守一定的格式

对于顶层的Config,
由两部分组成
- Namespace Config - 命名空间配置
- Global Config - 全局配置

例:
```json
{
    "namespace0":{
        "config0":"value0",
        "config1":[
            "value1",
            "value2"
        ],
        "config2":{
            "config3":"value3",
        }
    },
    "namespace1":{

    },
    "global":{
        "config4":"value4"
    }
}
```

在传递给Session时, 应该有将命名空间配置设置global默认值的操作

```python
for name, value in config.items():
    if name == 'global':
        continue
    value.setdefault(config['global'])
```
