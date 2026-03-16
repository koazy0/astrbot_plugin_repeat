"""
猜拳功能模块
"""
import random
from .base import BaseFeature
from typing import Generator, Optional
from astrbot.api.all import *


class RPSFeature(BaseFeature):
    """石头剪刀布功能"""

    def __init__(self):
        super().__init__("rps")
        self.command_prefix = "猜拳 "
        self.choices = ["石头", "剪刀", "布"]

    async def can_handle(self, message: str) -> bool:
        """判断是否能处理"""
        return message.startswith(self.command_prefix)

    async def handle(self, event: AstrMessageEvent, message: str, sender_name: str) -> Optional[Generator]:
        """处理猜拳"""
        # 提取用户选择
        user_choice = message.split(" ", 1)[1].strip()
        
        if user_choice not in self.choices:
            yield event.plain_result("请选择：石头、剪刀或布")
            return

        bot_choice = random.choice(self.choices)
        result = self._determine_winner(user_choice, bot_choice, sender_name)
        yield event.plain_result(f"👊 {sender_name} 出了 {user_choice}，bot 出了 {bot_choice}\n{result}")

    def _determine_winner(self, user: str, bot: str, sender_name: str) -> str:
        """判断胜负"""
        if user == bot:
            return "平局！"
        elif ((user == "石头" and bot == "剪刀") or
              (user == "剪刀" and bot == "布") or
              (user == "布" and bot == "石头")):
            return f"{sender_name} 赢了！"
        else:
            return "bot 赢了！"
