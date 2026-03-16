"""
被动事件模块
包含所有自动触发的功能
"""
from .consecutive_repeater import ConsecutiveRepeater
from .random_repeater import RandomRepeater

__all__ = ['ConsecutiveRepeater', 'RandomRepeater']
