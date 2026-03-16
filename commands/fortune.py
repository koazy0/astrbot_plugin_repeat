"""
抽签功能模块
"""
import random
from .base import BaseFeature
from typing import Generator, Optional
from astrbot.api.all import *


class FortuneFeature(BaseFeature):
    """抽签功能"""

    def __init__(self):
        super().__init__("fortune")
        self.command = "抽签"
        self.fortunes = [
            "大吉 - 今天运势极佳！",
            "中吉 - 不错的日子呢",
            "小吉 - 平平淡淡才是真",
            "末吉 - 还可以啦",
            "凶 - 小心行事",
            "大凶 - ...今天还是别出门了吧"
        ]

    async def can_handle(self, message: str) -> bool:
        """判断是否能处理"""
        return message == self.command

    async def handle(self, event: AstrMessageEvent, message: str, sender_name: str) -> Optional[Generator]:
        """处理抽签"""
        fortune = random.choice(self.fortunes)
        yield event.plain_result(f"🔮 {sender_name} 的签文：{fortune}")
