"""
复读bot插件主程序
插件入口，负责消息路由和模块协调
"""
from astrbot.api.all import *
from astrbot.api.event import filter
import sys
from pathlib import Path

# 添加插件根目录到 Python 路径
plugin_path = Path(__file__).parent
sys.path.insert(0, str(plugin_path))

from passive_events import ConsecutiveRepeater, RandomRepeater
from commands import FeatureManager
import logging


@register("repeater", "无辜猫猫", "复读bot", "1.0.0")
class RepeaterPlugin(Star):
    """复读插件主类"""

    def __init__(self, context: Context):
        super().__init__(context)
        self.config = context.get_config()

        # 初始化日志
        self._setup_logger()
        self.logger.info("复读插件初始化中...")

        # 初始化连续复读模式
        self.consecutive_repeater = ConsecutiveRepeater()

        # 初始化随机复读模式（20%概率）
        self.random_repeater = RandomRepeater(repeat_probability=0.2)

        # 初始化功能管理器
        self.feature_manager = FeatureManager()

        self.logger.info(f"已注册功能: {', '.join(self.feature_manager.get_registered_features())}")
        self.logger.info("复读插件初始化完成")

    def _setup_logger(self):
        """配置日志"""
        self.logger = logging.getLogger('RepeaterPlugin')
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """处理群消息"""
        try:
            group_id = str(event.message_obj.group_id)
            message_str = event.message_str.strip()
            sender_name = event.get_sender_name()
            sender_id = str(event.get_sender_id())

            self.logger.info(f"[复读插件] 收到消息 - 群:{group_id} 用户:{sender_name} 内容:{message_str}")

            # === 连续复读模式处理 ===
            # 记录消息
            self.consecutive_repeater.record_message(group_id, message_str, sender_id)

            # 检查连续复读（独立判断）
            consecutive_result = await self.consecutive_repeater.handle(event, message_str, sender_id)
            if consecutive_result:
                self.logger.info(f"[复读插件] 连续复读触发: {message_str}")

            # === 随机复读模式处理 ===
            # 独立判断，不受连续复读影响
            random_result = await self.random_repeater.handle(event, message_str)
            if random_result:
                self.logger.info(f"[复读插件] 随机复读触发: {message_str}")

            # === 发送复读结果 ===
            # 如果两个都触发，优先发送连续复读（避免重复发送）
            if consecutive_result:
                yield consecutive_result
            elif random_result:
                yield random_result

            # === 指令功能处理 ===
            # 分发到其他功能模块（签到、问候等）
            async for result in self.feature_manager.dispatch(event, message_str, sender_name):
                yield result

        except Exception as e:
            self.logger.error(f"[复读插件] 消息处理异常: {e}")
            import traceback
            traceback.print_exc()
