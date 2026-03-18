"""
抽烟指令功能
支持多种方式指定目标用户和时长
"""
import re
from astrbot.api.all import *
from astrbot.api.event import filter
from utils.ban import BanUtils


class BanCommand:
    """抽烟指令功能类"""

    def __init__(self, plugin_instance):
        """
        初始化抽烟指令
        
        Args:
            plugin_instance: 主插件实例
        """
        self.plugin = plugin_instance
        self.logger = plugin_instance.logger

    async def _get_group_members(self, event: AstrMessageEvent, group_id: int) -> dict:
        """获取群成员列表"""
        try:
            if hasattr(event.bot, "get_group_member_list"):
                member_list = await event.bot.get_group_member_list(group_id=group_id)
                # 构建成员映射：昵称->用户ID, QQ号->用户ID, 群名片->用户ID
                members = {}
                for member in member_list:
                    user_id = member.get("user_id") if isinstance(member, dict) else getattr(member, "user_id", None)
                    nickname = member.get("nickname", "") if isinstance(member, dict) else getattr(member, "nickname", "")
                    card = member.get("card", "") if isinstance(member, dict) else getattr(member, "card", "")
                    
                    if user_id:
                        # QQ号映射
                        members[str(user_id)] = user_id
                        # 昵称映射
                        if nickname:
                            members[nickname] = user_id
                        # 群名片映射
                        if card:
                            members[card] = user_id
                
                return members
        except Exception as e:
            self.logger.error(f"获取群成员列表失败: {e}")
        
        return {}

    def _parse_at_message(self, message: str) -> list:
        """解析@消息，提取被@的用户ID"""
        # 匹配@消息格式：[CQ:at,qq=用户ID]
        at_pattern = r'\[CQ:at,qq=(\d+)\]'
        matches = re.findall(at_pattern, message)
        return [int(match) for match in matches]

    def _parse_smoke_command(self, message: str) -> tuple:
        """
        解析抽烟指令
        
        Args:
            message: 完整的消息内容
            
        Returns:
            tuple: (target_identifier, duration_minutes)
                target_identifier: 目标标识符（可能是昵称、QQ号等），None表示自己
                duration_minutes: 时长（分钟）
        """
        # 移除指令前缀
        content = message.replace("/抽烟", "").replace("抽烟", "").strip()
        
        if not content:
            # 只有指令，禁言自己1分钟
            return None, 1
        
        # 检查是否有@消息
        at_users = self._parse_at_message(content)
        if at_users:
            # 有@消息，取第一个被@的用户
            # 解析时长参数
            # 移除@标签后解析剩余参数
            clean_content = re.sub(r'\[CQ:at,qq=\d+\]', '', content).strip()
            parts = clean_content.split()
            
            duration = 1  # 默认1分钟
            if parts:
                try:
                    duration = max(1, min(60, int(parts[0])))  # 限制在1-60分钟
                except ValueError:
                    duration = 1
            
            return at_users[0], duration
        
        # 没有@消息，解析文本参数
        parts = content.split()
        if len(parts) == 0:
            return None, 1
        elif len(parts) == 1:
            # 只有目标，默认1分钟
            return parts[0], 1
        else:
            # 有目标和时长
            target = parts[0]
            try:
                duration = max(1, min(60, int(parts[1])))  # 限制在1-60分钟
            except ValueError:
                duration = 1
            return target, duration

    async def _resolve_target_user(self, event: AstrMessageEvent, target_identifier) -> int:
        """
        解析目标用户ID
        
        Args:
            event: 消息事件
            target_identifier: 目标标识符（可能是昵称、QQ号、群名片等）
            
        Returns:
            int: 用户ID，如果找不到返回None
        """
        if target_identifier is None:
            # 目标是自己
            return int(event.get_sender_id())
        
        # 如果是数字，直接当作QQ号
        if isinstance(target_identifier, int):
            return target_identifier
        
        if isinstance(target_identifier, str) and target_identifier.isdigit():
            return int(target_identifier)
        
        # 获取群成员列表进行匹配
        group_id = BanUtils.get_group_id(event)
        if not group_id:
            return None
        
        members = await self._get_group_members(event, group_id)
        
        # 在成员列表中查找匹配
        if target_identifier in members:
            return members[target_identifier]
        
        # 模糊匹配昵称或群名片
        for name, user_id in members.items():
            if target_identifier in name or name in target_identifier:
                return user_id
        
        return None

    async def smoke_command(self, event: AstrMessageEvent):
        """抽烟指令 - 支持多种目标指定方式"""
        try:
            group_id = BanUtils.get_group_id(event)
            if not group_id:
                yield event.plain_result("❌ 仅限群聊使用")
                return

            # 解析指令参数
            target_identifier, duration_minutes = self._parse_smoke_command(event.message_str or "")
            
            self.logger.info(f"🚬 抽烟指令 - 目标:{target_identifier}, 时长:{duration_minutes}分钟")
            
            # 解析目标用户ID
            target_user_id = await self._resolve_target_user(event, target_identifier)
            
            if target_user_id is None:
                yield event.plain_result("❌ 找不到指定的用户")
                return
            
            # 获取目标用户昵称
            target_name = "目标用户"
            if target_user_id == int(event.get_sender_id()):
                target_name = BanUtils.get_user_name(event)
            else:
                # 尝试从群成员列表获取昵称
                members = await self._get_group_members(event, group_id)
                for name, user_id in members.items():
                    if user_id == target_user_id and not name.isdigit():
                        target_name = name
                        break
            
            self.logger.info(f"🚬 准备禁言用户 {target_name}({target_user_id})，时长 {duration_minutes} 分钟")
            
            # 转换为秒
            duration_seconds = duration_minutes * 60
            
            # 执行禁言
            ban_result = await BanUtils.ban_user(event, target_user_id, duration_seconds, self.logger)
            
            if ban_result > 0:
                formatted_duration = BanUtils.format_ban_duration(ban_result)
                if target_user_id == int(event.get_sender_id()):
                    yield event.plain_result(f"🚬 {target_name} 开始抽烟，禁言 {formatted_duration}")
                else:
                    yield event.plain_result(f"🚬 {target_name} 被强制抽烟，禁言 {formatted_duration}")
            else:
                yield event.plain_result(f"❌ 无法让 {target_name} 抽烟！可能是权限不足或目标是管理员")
                
        except Exception as e:
            self.logger.error(f"抽烟指令失败: {e}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
            yield event.plain_result("❌ 抽烟失败，请重试")

    async def test_smoke(self, event: AstrMessageEvent):
        """测试方法 - 确认方法存在"""
        yield event.plain_result("🚬 抽烟功能测试成功！")

    # 保留旧的方法以兼容性
    async def ban_test_command(self, event: AstrMessageEvent):
        """禁言测试指令 - 重定向到抽烟指令"""
        async for result in self.smoke_command(event):
            yield result

    async def ban_user_command(self, event: AstrMessageEvent):
        """禁言指定用户指令 - 重定向到抽烟指令"""
        async for result in self.smoke_command(event):
            yield result