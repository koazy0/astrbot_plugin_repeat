"""
问候功能模块 - 展示带参数的命令路由
"""
from .base import BaseFeature
from typing import Generator, Optional
from astrbot.api.all import *


class GreetFeature(BaseFeature):
    """问候功能 - 支持 /greet 命令，可带参数"""

    def __init__(self):
        super().__init__("greet")
        self.command_prefix = "/greet"
        self.greetings = {
            "早上": "早上好！新的一天开始了 ☀️",
            "中午": "中午好！记得吃饭哦 🍜",
            "晚上": "晚上好！好好休息 🌙",
            "晚安": "晚安！做个好梦 😴"
        }

    async def can_handle(self, message: str) -> bool:
        """判断是否能处理 - 匹配 /greet 命令"""
        return message.startswith(self.command_prefix)

    async def handle(self, event: AstrMessageEvent, message: str, sender_name: str) -> Optional[Generator]:
        """处理问候"""
        # 解析命令参数
        parts = message.split()
        
        if len(parts) == 1:
            # 无参数：返回默认问候
            yield event.plain_result(f"你好呀，{sender_name}！👋")
        elif len(parts) == 2:
            # 有参数：匹配问候类型
            param = parts[1]
            if param in self.greetings:
                yield event.plain_result(f"{self.greetings[param]}，{sender_name}！")
            else:
                yield event.plain_result(
                    f"❓ 不认识的问候类型：{param}\n"
                    f"支持的类型：{', '.join(self.greetings.keys())}"
                )
        else:
            yield event.plain_result("格式错误，使用：/greet [类型]")
