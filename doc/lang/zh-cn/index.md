# AI-Completer

AI-Completer 是一个命令事件循环器, 在不同的接口中交换信息, 调用命令, 以及进一步处理等
其中接口分为 AI接口, 系统接口, 用户接口等

AI-Completer 主要由以下部分组成:
- [Handler](handler.md): 主循环器, 将由其处理命令调用和接口兼容性
- [Interface](interface.md): 接口模板, 创建接口, 引入命令, 自定义解析内容
- [session](session.md): 会话, AI-Completer 是多任务并行的, 会话是存储单个任务的结构
- [ai](ai.md): AI架构相关, 这里主要存储了 Transformer 模型类的相关接口
- [implements](implements.md): 实现, 这里有一些默认的interface实例, 如控制台接口, AI Helper等
- [memory](memory.md): 记忆模块, 正在开发中...
