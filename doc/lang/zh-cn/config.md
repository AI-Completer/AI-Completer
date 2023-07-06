# Config

消歧义:
- [配置类 Class Config](class/config.md)
- 配置文件

配置文件, 为遵循json格式和[Class Config格式](class/config.md#格式)的文件, 默认文件名是config.json

## 所有可用配置

在模块主函数中启动时,
以下是所有implemented interfaces / ai可用配置
```json
{
    "global":{                      // 全局配置
        "debug": false,             // 调试选项
        "proxy": ""                 // 全局代理
    },
    "openaichat":{                  // OpenAI AI Chater 选项, 非接口调用
        "sys":{
            "prompt": "You are ChatGPT created by OpenAI. Your task is to assist user.",      // 最初的System提示
            "max-token": 2048       // 最大token数, 该数将不计入system提示
        },
        "chat":{                    // Chat参数, 参见官方网站 API Reference https://platform.openai.com/docs/api-reference/chat/create
            
        },
        "openai":{
            "api-key": "sk-..."     // OpenAI API密钥 https://platform.openai.com/account/api-keys
        }
    },
}
```
