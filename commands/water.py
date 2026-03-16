"""
喝水功能模块
"""
import random
from .base import BaseFeature
from typing import Generator, Optional
from astrbot.api.all import *


class WaterFeature(BaseFeature):
    """喝水功能"""

    def __init__(self):
        super().__init__("water")
        self.keyword = "喝水"
        self.responses = [
            "{} 喝了一口水",
            "{} 大口喝水",
            "咕嘟咕嘟... {} 喝完了",
            "💧 {} 正在补充水分"
        ]

    async def can_handle(self, message: str) -> bool:
        """判断是否能处理"""
        return self.keyword in message

    async def handle(self, event: AstrMessageEvent, message: str, sender_name: str) -> Optional[Generator]:
        """处理喝水"""
        response = random.choice(self.responses).format(sender_name)
        yield event.plain_result(response)
