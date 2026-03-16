"""
指令功能模块 - 用户主动触发的命令
"""
from .base import BaseFeature
from .manager import FeatureManager

# 导出具体功能
from .dice import DiceFeature
from .fortune import FortuneFeature
from .rps import RPSFeature
from .sign_in import SignInFeature
from .greet import GreetFeature
from .random_number import RandomNumberFeature
from .water import WaterFeature

__all__ = [
    # 基础类
    'BaseFeature',
    'FeatureManager',
    # 具体功能
    'DiceFeature',
    'FortuneFeature',
    'RPSFeature',
    'SignInFeature',
    'GreetFeature',
    'RandomNumberFeature',
    'WaterFeature'
]
