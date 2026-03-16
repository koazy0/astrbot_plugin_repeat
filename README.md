# 复读bot插件 README

## 一、插件概述
基于 `AstrBot` 的群聊复读与娱乐插件，支持智能复读功能，并附带多种臊皮娱乐功能。

## 二、插件信息
- **插件名称**：repeater
- **作者**：无辜猫猫
- **版本**：v1.0.0

## 三、项目结构

```
astrbot_plugin_rg/
├── main.py                          # 插件入口
├── metadata.yaml                    # 插件元数据
├── README.md                        # 项目文档
│
├── commands/                        # 📋 指令功能模块
│   ├── __init__.py                 # 模块导出
│   ├── base.py                     # 功能基类
│   ├── manager.py                  # 功能管理器（责任链）
│   ├── sign_in.py                 # 签到功能
│   ├── greet.py                   # 问候功能
│   ├── dice.py                    # 骰子功能
│   ├── fortune.py                 # 抽签功能
│   ├── rps.py                     # 猜拳功能
│   ├── random_number.py           # 随机数功能
│   └── water.py                   # 喝水功能
│
├── passive_events/                  # 🔄 被动事件模块
│   ├── __init__.py
│   └── repeater.py                # 复读机
│
├── utils/                           # 🛠️ 工具模块
│   ├── __init__.py
│   └── logger.py                  # 日志工具
│
├── llm/                             # 🤖 LLM功能（预留）
├── maimai/                          # 🎮 舞萌功能（预留）
│
└── *.bak                           # 备份文件
```

## 四、框架说明

### 4.1 commands/ - 指令功能模块

**职责**：管理所有用户主动触发的命令功能

**核心组件**：

#### base.py - 功能基类
```python
class BaseFeature(ABC):
    def __init__(self, name: str, description: str = "")

    @abstractmethod
    async def can_handle(self, message: str) -> bool:
        """判断是否能处理该消息"""

    @abstractmethod
    async def handle(self, event, message, sender_name):
        """处理消息"""
```

#### manager.py - 功能管理器
```python
class FeatureManager:
    def register(feature)              # 注册功能
    def unregister(feature_name)        # 注销功能
    async def dispatch(event, message, sender_name)  # 分发消息
    def get_registered_features()      # 获取已注册功能
```

**工作流程**：
```
用户命令 → FeatureManager.dispatch()
    ↓
遍历已注册的功能
    ↓
can_handle() 检查
    ↓
匹配到 → handle() 处理 → 返回
```

### 4.2 passive_events/ - 被动事件模块

**职责**：管理自动触发的功能（如复读）

**特点**：
- 自动监听所有消息
- 不参与责任链路由
- 在 main.py 中独立调用

---

## 五、指令功能说明

### 5.1 sign_in.py - 签到功能

**命令**：`/sign`

**功能**：每日签到，记录签到天数和连续签到

**响应示例**：
```
🎉 用户 签到成功！
📊 连续签到：3 天
📈 累计签到：15 天
🎁 本次奖励：16 金币
```

---

### 5.2 greet.py - 问候功能

**命令**：`/greet [类型]`

**支持的类型**：早上、中午、晚上、晚安

**响应示例**：
```
/greet → 你好呀，用户！👋
/greet 早上 → 早上好！新的一天开始了 ☀️，用户！
```

---

### 5.3 dice.py - 骰子功能

**命令**：`掷骰子` 或 `丢骰子`

**功能**：随机掷出1-6点

**响应示例**：
```
🎲 用户 掷出了 3 点！
```

---

### 5.4 fortune.py - 抽签功能

**命令**：`抽签`

**功能**：随机抽取运势签文

**包含的运势**：大吉、中吉、小吉、末吉、凶、大凶

**响应示例**：
```
🔮 用户的签文：大吉 - 今天运势极佳！
```

---

### 5.5 rps.py - 猜拳功能

**命令**：`猜拳 石头/剪刀/布`

**功能**：与 bot 进行石头剪刀布对决

**响应示例**：
```
👊 用户 出了 石头，bot 出了 剪刀
用户 赢了！
```

---

### 5.6 water.py - 喝水功能

**触发**：消息中包含"喝水"

**功能**：随机输出喝水相关回复

**响应示例**：
```
我今天要喝水
→ 💧 用户 正在补充水分
```

---

### 5.7 random_number.py - 随机数功能

**命令**：`随机 开始值 结束值`

**功能**：生成指定范围的随机整数

**响应示例**：
```
随机 1 100
→ 🎲 随机数：42（1-100）
```

---

## 六、被动事件说明

### 6.1 repeater.py - 复读机

**触发条件**：群内出现连续3条相同消息

**功能特性**：
- 80% 概率正常复读
- 20% 概率小声复读
- 复读后自动清空历史

**响应示例**：
```
用户A: 大家好
用户B: 大家好
用户C: 大家好
→ 大家好（复读）
```

---

## 七、技术特性

- **责任链模式**：`FeatureManager` 统一分发指令
- **策略模式**：`BaseFeature` 定义统一接口
- **单例模式**：`MessageHistory` 管理消息历史
- **异步处理**：基于 asyncio 的完整异步架构
- **易于扩展**：添加功能只需创建文件并注册

---

## 八、开发指南

### 8.1 添加新指令功能

**步骤 1**：在 `commands/` 创建文件
```python
from commands.base import BaseFeature

class NewFeature(BaseFeature):
    def __init__(self):
        super().__init__(
            name="new_feature",
            description="新功能描述"
        )

    async def can_handle(self, message: str) -> bool:
        return message == "/newcommand"

    async def handle(self, event, message, sender_name):
        yield event.plain_result("新功能！")
```

**步骤 2**：在 `commands/__init__.py` 导出
```python
from .new_feature import NewFeature

__all__ = [..., 'NewFeature']
```

**步骤 3**：在 `commands/manager.py` 注册
```python
self.register(NewFeature())
```

---

## 九、更新日志

### v1.0.0
- 初始版本发布
- 实现基础复读功能
- 添加签到、问候、骰子等娱乐功能
- 实现模块化架构
