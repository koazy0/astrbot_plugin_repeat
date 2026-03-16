"""
骰子功能模块
"""
import random
from commands.base import BaseFeature
from typing import Generator, Optional
from astrbot.api.all import *


class DiceFeature(BaseFeature):
    """骰子功能"""

    def __init__(self):
        super().__init__(
            name="dice",
            description="掷骰子游戏"
        )
        self.commands = ["掷骰子", "丢骰子"]

    async def can_handle(self, message: str) -> bool:
        """判断是否能处理"""
        return message in self.commands

    async def handle(self, event: AstrMessageEvent, message: str, sender_name: str) -> Optional[Generator]:
        """处理骰子"""
        result = random.randint(1, 6)
        yield event.plain_result(f"🎲 {sender_name} 掷出了 {result} 点！")
