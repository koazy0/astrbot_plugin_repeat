"""
功能基类 - 所有指令功能的统一接口
"""
from abc import ABC, abstractmethod
from typing import Generator, Optional
from astrbot.api.all import *


class BaseFeature(ABC):
    """功能模块基类 - 所有指令功能都应继承此类"""

    def __init__(self, name: str, description: str = ""):
        """
        初始化功能模块

        Args:
            name: 功能名称（唯一标识）
            description: 功能描述
        """
        self.name = name
        self.description = description

    @abstractmethod
    async def can_handle(self, message: str) -> bool:
        """
        判断是否能处理该消息

        Args:
            message: 用户消息

        Returns:
            bool: 是否能处理
        """
        pass

    @abstractmethod
    async def handle(self, event: AstrMessageEvent, message: str, sender_name: str) -> Optional[Generator]:
        """
        处理消息

        Args:
            event: 消息事件对象
            message: 消息内容
            sender_name: 发送者名称

        Yields:
            响应结果
        """
        pass

    def get_name(self) -> str:
        """获取功能名称"""
        return self.name

    def get_description(self) -> str:
        """获取功能描述"""
        return self.description

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
