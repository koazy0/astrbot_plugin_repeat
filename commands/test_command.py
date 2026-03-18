"""
测试指令功能
演示如何通过组合方式将指令功能集成到主插件中
"""
import random
from astrbot.api.all import *
from astrbot.api.event import filter


class TestCommand:
    """测试指令功能类"""

    def __init__(self, plugin_instance):
        """
        初始化测试指令
        
        Args:
            plugin_instance: 主插件实例，用于访问日志等
        """
        self.plugin = plugin_instance
        self.logger = plugin_instance.logger

    def register_commands(self):
        """
        注册指令到主插件
        返回装饰器方法的字典
        """
        return {
            "测试": self.test_command
        }

    #@filter.command("测试")
    async def test_command(self, event: AstrMessageEvent):
        """
        测试指令的具体实现
        
        Args:
            event: 消息事件对象
            
        Yields:
            响应结果
        """
        try:
            sender_name = event.get_sender_name()
            message = event.message_str.strip()
            
            self.logger.info(f"测试指令被调用，发送者: {sender_name}, 消息: {message}")
            
            # 生成随机测试结果
            test_results = [
                "✅ 测试通过！系统运行正常",
                "🔧 测试完成，发现一些小问题",
                "⚡ 测试结果：性能优秀！",
                "🎯 测试成功，命中目标！",
                "🚀 测试完毕，准备起飞！"
            ]
            
            result = random.choice(test_results)
            yield event.plain_result(f"🧪 {sender_name} 执行了测试\n{result}")
            
        except Exception as e:
            self.logger.error(f"测试指令失败: {e}")
            yield event.plain_result("❌ 测试失败，请重试")