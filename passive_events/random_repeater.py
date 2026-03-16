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

    功能：当任何人发送消息时，有20%的概率触发复读
    该模式独立于连续复读，随时生效
    """

    def __init__(self, repeat_probability: float = 0.2):
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

    def should_repeat(self, group_id: str) -> bool:
        """判断是否应该复读

        Args:
            group_id: 群聊ID

        Returns:
            bool: 是否应该复读
        """
        # 检查是否刚刚复读过，避免复读自己的复读
        if group_id in self._last_repeat_groups:
            self._last_repeat_groups.remove(group_id)
            return False

        # 随机判断是否复读
        return random.random() < self.repeat_probability

    async def handle(
        self,
        event: AstrMessageEvent,
        message: str
    ) -> Optional[str]:
        """处理复读逻辑

        Args:
            event: 消息事件
            message: 消息内容

        Returns:
            Optional[str]: 复读结果或None
        """
        group_id = str(event.message_obj.group_id)

        # 判断是否应该复读
        if not self.should_repeat(group_id):
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
