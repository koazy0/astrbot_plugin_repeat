"""
统一的禁言工具模块
提供统一的禁言功能，供所有指令使用
"""
import random
from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent


class BanUtils:
    """禁言工具类"""
    
    @staticmethod
    def get_group_id(event: AstrMessageEvent) -> int:
        """获取群ID"""
        return getattr(event.message_obj, "group_id", None)

    @staticmethod
    def get_user_name(event: AstrMessageEvent) -> str:
        """获取用户昵称"""
        return event.get_sender_name() or "玩家"

    @staticmethod
    def format_ban_duration(seconds: int) -> str:
        """格式化禁言时长显示"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds > 0:
                return f"{minutes}分{remaining_seconds}秒"
            else:
                return f"{minutes}分钟"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            if remaining_minutes > 0:
                return f"{hours}小时{remaining_minutes}分钟"
            else:
                return f"{hours}小时"

    @staticmethod
    async def is_user_bannable(event: AstrMessageEvent, user_id: int, logger=None) -> bool:
        """检查用户是否可以被禁言（不是群主或管理员）"""
        try:
            group_id = BanUtils.get_group_id(event)
            if not group_id:
                if logger:
                    logger.warning("❌ 无法获取群ID，无法检查用户权限")
                return False

            # 调用API获取群成员信息
            if hasattr(event.bot, "get_group_member_info"):
                member_info = await event.bot.get_group_member_info(
                    group_id=group_id, user_id=user_id, no_cache=True
                )

                # 检查角色
                role = (
                    member_info.get("role", "member")
                    if isinstance(member_info, dict)
                    else getattr(member_info, "role", "member")
                )

                # 群主和管理员不能被禁言
                if role in ["owner", "admin"]:
                    if logger:
                        logger.info(f"用户 {user_id} 是{role}，跳过禁言")
                    return False

                return True

            # 如果无法获取信息，默认可以禁言（兼容旧版本）
            return True
        except Exception as e:
            if logger:
                logger.error(f"检查用户可禁言状态失败: {e}")
            # 出错时默认可以禁言，避免游戏卡住
            return True

    @staticmethod
    async def ban_user(event: AstrMessageEvent, user_id: int, duration: int, logger=None) -> int:
        """
        禁言用户 - 统一的禁言实现
        
        Args:
            event: 消息事件对象
            user_id: 要禁言的用户ID
            duration: 禁言时长（秒）
            logger: 日志记录器（可选）
            
        Returns:
            实际禁言时长（秒），如果禁言失败返回 0
        """
        if logger:
            logger.info(f"🔍 BanUtils.ban_user被调用 - user_id:{user_id}, duration:{duration}")
        
        group_id = BanUtils.get_group_id(event)
        if not group_id:
            if logger:
                logger.warning("❌ 无法获取群ID，跳过禁言")
            return 0

        if logger:
            logger.info(f"🔍 获取到群ID: {group_id} (类型: {type(group_id)})")

        # 检查是否可以禁言该用户
        bannable = await BanUtils.is_user_bannable(event, user_id, logger)
        if logger:
            logger.info(f"🔍 用户是否可禁言: {bannable}")
        
        if not bannable:
            user_name = BanUtils.get_user_name(event)
            if logger:
                logger.info(f"⏭️ 用户 {user_name}({user_id}) 是管理员/群主，跳过禁言")
            return 0

        formatted_duration = BanUtils.format_ban_duration(duration)
        if logger:
            logger.info(f"🔍 禁言时长: {duration}秒 ({formatted_duration})")

        try:
            has_method = hasattr(event.bot, "set_group_ban")
            if logger:
                logger.info(f"🔍 Bot是否有set_group_ban方法: {has_method}")
            
            if has_method:
                if logger:
                    logger.info(f"🎯 准备调用API - 群:{group_id}({type(group_id)}), 用户:{user_id}({type(user_id)}), 时长:{duration}({type(duration)})")
                
                result = await event.bot.set_group_ban(
                    group_id=group_id, user_id=user_id, duration=duration
                )
                
                if logger:
                    logger.info(f"🔍 API调用结果: {result}")
                    logger.info(f"✅ 用户 {user_id} 在群 {group_id} 被禁言 {formatted_duration}")
                
                return duration
            else:
                if logger:
                    logger.error("❌ Bot 没有 set_group_ban 方法，无法禁言")
                    logger.error("💡 提示：请检查机器人适配器是否支持禁言功能")
                return 0
        except Exception as e:
            if logger:
                logger.error(f"❌ 禁言用户失败: {e}")
                logger.error(f"❌ 异常类型: {type(e).__name__}")
                import traceback
                logger.error(f"❌ 完整异常信息:\n{traceback.format_exc()}")
            
            # 检查是否是权限问题
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["permission", "权限", "privilege", "insufficient"]):
                if logger:
                    logger.error("🔐 权限不足：请检查机器人是否有群管理权限！")
                    logger.error("💡 解决方法：将机器人设置为群管理员")

        return 0

    @staticmethod
    async def ban_user_random(event: AstrMessageEvent, user_id: int, min_ban: int = 60, max_ban: int = 300, logger=None) -> int:
        """
        禁言用户（随机时长）
        
        Args:
            event: 消息事件对象
            user_id: 要禁言的用户ID
            min_ban: 最小禁言时长（秒）
            max_ban: 最大禁言时长（秒）
            logger: 日志记录器（可选）
            
        Returns:
            实际禁言时长（秒），如果禁言失败返回 0
        """
        duration = random.randint(min_ban, max_ban)
        return await BanUtils.ban_user(event, user_id, duration, logger)