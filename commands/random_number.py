"""
随机数功能模块
"""
import random
from .base import BaseFeature
from typing import Generator, Optional
from astrbot.api.all import *


class RandomNumberFeature(BaseFeature):
    """随机数功能"""

    def __init__(self):
        super().__init__("random_number")
        self.prefixes = ["随机 ", "random "]

    async def can_handle(self, message: str) -> bool:
        """判断是否能处理"""
        return any(message.startswith(prefix) for prefix in self.prefixes)

    async def handle(self, event: AstrMessageEvent, message: str, sender_name: str) -> Optional[Generator]:
        """处理随机数"""
        try:
            parts = message.split()
            if len(parts) == 3:
                start = int(parts[1])
                end = int(parts[2])
                result = random.randint(start, end)
                yield event.plain_result(f"🎲 随机数：{result}（{start}-{end}）")
        except ValueError:
            yield event.plain_result("格式错误，请使用：随机 开始值 结束值")
