"""
功能管理器 - 责任链模式
负责管理所有指令功能并进行消息分发
"""
from typing import List
from .base import BaseFeature
from .dice import DiceFeature
from .fortune import FortuneFeature
from .rps import RPSFeature
from .sign_in import SignInFeature
from .greet import GreetFeature
from .random_number import RandomNumberFeature
from .water import WaterFeature


class FeatureManager:
    """功能管理器 - 负责注册和调度各个功能模块"""

    def __init__(self):
        """初始化管理器"""
        self.features: List[BaseFeature] = []
        self._register_default_features()

    def _register_default_features(self):
        """注册默认功能"""
        self.register(SignInFeature())      # /sign - 签到
        self.register(GreetFeature())        # /greet - 问候
        self.register(DiceFeature())         # 掷骰子
        self.register(FortuneFeature())      # 抽签
        self.register(RPSFeature())           # 猜拳
        self.register(WaterFeature())         # 喝水
        self.register(RandomNumberFeature()) # 随机数

    def register(self, feature: BaseFeature):
        """
        注册功能

        Args:
            feature: 功能模块实例
        """
        self.features.append(feature)

    def unregister(self, feature_name: str):
        """
        注销功能

        Args:
            feature_name: 功能名称
        """
        self.features = [f for f in self.features if f.get_name() != feature_name]

    async def dispatch(self, event, message: str, sender_name: str):
        """
        分发消息到合适的功能处理

        Args:
            event: 消息事件对象
            message: 消息内容
            sender_name: 发送者名称

        Yields:
            响应结果
        """
        for feature in self.features:
            if await feature.can_handle(message):
                async for result in feature.handle(event, message, sender_name):
                    yield result
                return  # 找到处理该消息的功能后，停止传播

    def get_registered_features(self) -> List[str]:
        """
        获取已注册的功能列表

        Returns:
            功能名称列表
        """
        return [f.get_name() for f in self.features]
