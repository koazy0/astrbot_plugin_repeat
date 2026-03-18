"""
连续复读模式
检测群聊中连续2条相同消息后进行复读
"""
import logging
from typing import Optional, Dict, Tuple
from astrbot.api.all import *


class ConsecutiveRepeater:
    """连续复读器 - 模式1

    功能：记录每个群聊的最后一条消息和连续出现次数
    当同一消息连续出现2次，且第2次不是自己发送时，触发复读
    """

    def __init__(self):
        # 群聊ID -> (最后一条消息, 连续次数) 的映射
        self._group_states: Dict[str, Tuple[str, int]] = {}

        # 记录复读后的群聊，防止复读自己
        self._last_repeat_groups: set = set()

        # 配置日志
        self.logger = logging.getLogger('ConsecutiveRepeater')
        self.logger.setLevel(logging.INFO)

    def _get_bot_id(self, event: AstrMessageEvent) -> str:
        """获取机器人自己的ID"""
        return str(event.message_obj.self_id)

    def record_message(self, group_id: str, message: str, sender_id: str):
        """记录消息并更新群聊状态

        Args:
            group_id: 群聊ID
            message: 消息内容
            sender_id: 发送者ID
        """
        # 获取当前群聊状态
        current_state = self._group_states.get(group_id, ("", 0))
        last_message, count = current_state

        # 更新状态
        if message == last_message:
            # 相同消息，次数+1
            count += 1
        else:
            # 不同消息，重置计数
            count = 1
            last_message = message

        self._group_states[group_id] = (last_message, count)

        self.logger.debug(f"群 {group_id}: 消息 '{message[:20]}...' 连续次数 {count}")
        self.logger.info(f"[连续复读] 群 {group_id} - 消息:'{message}' 计数:{count}")

    def should_repeat(self, group_id: str, message: str, sender_id: str, bot_id: str) -> bool:
        """判断是否应该复读

        Args:
            group_id: 群聊ID
            message: 消息内容
            sender_id: 发送者ID
            bot_id: 机器人ID

        Returns:
            bool: 是否应该复读
        """
        # 防止复读机器人自己的消息
        if sender_id == bot_id:
            return False

        # 防止复读指令消息
        if self._is_command_message(message):
            return False

        state = self._group_states.get(group_id)
        if not state:
            return False

        last_message, count = state

        # 连续2条相同消息时触发复读
        if count >= 2 and message == last_message:
            return True

        return False

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
        bot_id = self._get_bot_id(event)

        # 判断是否应该复读
        if not self.should_repeat(group_id, message, sender_id, bot_id):
            return None

        # 标记该群聊刚刚复读过
        self._last_repeat_groups.add(group_id)

        # 清空计数，恢复为0
        self._group_states[group_id] = (message, 0)

        self.logger.info(f"群 {group_id} 触发连续复读: '{message[:30]}...'")

        # 正常复读
        return event.plain_result(message)

    def clear_group_state(self, group_id: str):
        """清空指定群聊的状态"""
        if group_id in self._group_states:
            del self._group_states[group_id]
        if group_id in self._last_repeat_groups:
            self._last_repeat_groups.remove(group_id)
