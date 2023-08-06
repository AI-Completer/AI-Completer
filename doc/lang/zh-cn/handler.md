# Handler

handler 是一个容器, 用于装载interface和command等, 并处理函数调用和权限管理

[源文件](/aicompleter/handler.py)

## 特点

Handler可以理解为一个事件循环器, 所有命令调用都在其记录, 权限审查。
用户通过ConsoleInterface等Interface来接入Handler这个集体, 向其它Interface(主要是AI), 发送命令, 由Command来判断,解析和调用命令,
所有的操作都记录在一个Session中

