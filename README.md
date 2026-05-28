# 微信自动化工具

基于 `uiautomation` 库实现的微信自动化工具，可以方便地进行微信的自动化操作。

## 功能特性

- ✅ 查找微信窗口
- ✅ 搜索并打开聊天
- ✅ 发送消息（单条/批量）
- ✅ 获取聊天列表
- ✅ 获取最新消息
- ✅ 聊天截图
- ✅ 窗口控制（最小化/最大化）
- ✅ 自动回复（演示）

## 环境要求

- Windows 系统
- Python 3.7+
- 微信 PC 版已安装并运行

## 安装

1. 克隆或下载本项目

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

### 方式一：运行示例脚本

```bash
python example.py
```

示例脚本提供了一个交互式菜单，可以选择不同的自动化功能。

### 方式二：在自己的代码中使用

```python
from wechat_automation import WeChatAutomation

# 创建自动化实例
wechat = WeChatAutomation()

# 查找微信窗口
if wechat.find_wechat_window():
    # 搜索聊天
    wechat.search_chat("文件传输助手")
    
    # 发送消息
    wechat.send_message("Hello, World!")
    
    # 获取聊天列表
    chats = wechat.get_chat_list()
    print(chats)
    
    # 截图
    wechat.screenshot_chat("screenshot.png")
```

## 核心 API

### WeChatAutomation 类

#### find_wechat_window()
查找微信主窗口
- 返回: bool - 是否找到

#### search_chat(chat_name: str)
搜索并打开指定聊天
- 参数: chat_name - 联系人或群名称
- 返回: bool - 是否成功

#### send_message(message: str)
发送消息
- 参数: message - 消息内容
- 返回: bool - 是否成功

#### get_chat_list()
获取聊天列表
- 返回: List[str] - 聊天名称列表

#### get_latest_messages(count: int)
获取最新消息
- 参数: count - 获取消息数量
- 返回: List[str] - 消息列表

#### screenshot_chat(filepath: str)
聊天截图
- 参数: filepath - 保存路径
- 返回: bool - 是否成功

## 配置

在 `config.py` 中可以修改以下配置：

```python
WECHAT_WINDOW_NAME = "微信"  # 微信窗口名称
TIMEOUT = 10                  # 操作超时时间（秒）
SLEEP_TIME = 1                # 操作间隔时间（秒）
DEBUG = True                  # 是否显示调试信息
SCREENSHOT_DIR = "screenshots"  # 截图保存路径
```

## 注意事项

⚠️ **重要提示：**
1. 使用前请确保微信已启动并登录
2. 自动化操作可能违反微信使用条款，请谨慎使用
3. 建议在测试账号上使用该工具
4. 频繁操作可能触发微信的安全机制

## 项目结构

```
weixin-auto/
├── wechat_automation.py    # 核心自动化模块
├── example.py              # 示例脚本
├── config.py               # 配置文件
├── requirements.txt        # 依赖包
└── README.md              # 说明文档
```

## 开发

### 添加新功能

在 `wechat_automation.py` 中的 `WeChatAutomation` 类添加新方法：

```python
def your_new_feature(self, param: str) -> bool:
    """新功能描述"""
    if not self.window:
        return False
    
    try:
        # 实现你的功能
        pass
    except Exception as e:
        if DEBUG:
            print(f"[错误] {e}")
        return False
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
