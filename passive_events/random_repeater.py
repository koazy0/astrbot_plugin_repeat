"""
随机复读模式
随机以20%的概率复读任意消息
"""
import random
import logging
from typing import Optional
from astrbot.api.all import *


class RandomRepeater:
    """随机复读器 - 模式2

    功能：当任何人发送消息时，有2%的概率触发复读
    """

    def __init__(self, repeat_probability: float = 0.02):
        """
        Args:
            repeat_probability: 复读概率，默认0.2（20%）
        """
        self.repeat_probability = repeat_probability

        # 记录复读后的群聊，防止复读自己的复读
        self._last_repeat_groups: set = set()

        # 配置日志
        self.logger = logging.getLogger('RandomRepeater')
        self.logger.setLevel(logging.INFO)

    def should_repeat(self, group_id: str, sender_id: str, bot_id: str, message: str) -> bool:
        """判断是否应该复读

        Args:
            group_id: 群聊ID
            sender_id: 发送者ID
            bot_id: 机器人ID
            message: 消息内容

        Returns:
            bool: 是否应该复读
        """
        # 防止复读机器人自己的消息
        if sender_id == bot_id:
            return False

        # 防止复读指令消息
        if self._is_command_message(message):
            return False

        # 随机判断是否复读
        return random.random() < self.repeat_probability

    def _is_command_message(self, message: str) -> bool:
        """判断是否是指令消息"""
        message = message.strip()
        
        # 检查所有指令
        commands = [
            "装填", "开枪", "状态", "帮助", "走火开", "走火关",
            "抽签", "掷骰子", "丢骰子", "猜拳", "随机", "喝水", 
            "测试", "sign", "greet"
        ]
        
        for cmd in commands:
            if message == cmd or message.startswith(cmd + " "):
                return True
                
        return False

    async def handle(
        self,
        event: AstrMessageEvent,
        message: str,
        sender_id: str
    ) -> Optional[str]:
        """处理复读逻辑

        Args:
            event: 消息事件
            message: 消息内容
            sender_id: 发送者ID

        Returns:
            Optional[str]: 复读结果或None
        """
        group_id = str(event.message_obj.group_id)
        bot_id = str(event.message_obj.self_id)

        # 判断是否应该复读
        if not self.should_repeat(group_id, sender_id, bot_id, message):
            return None

        # 标记该群聊刚刚复读过
        self._last_repeat_groups.add(group_id)

        self.logger.info(f"群 {group_id} 触发随机复读: '{message[:30]}...'")

        # 正常复读
        return event.plain_result(message)

    def clear_group_state(self, group_id: str):
        """清空指定群聊的状态"""
        if group_id in self._last_repeat_groups:
            self._last_repeat_groups.remove(group_id)
