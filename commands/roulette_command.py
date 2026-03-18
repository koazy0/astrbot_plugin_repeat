"""
俄罗斯轮盘指令功能
基于example.py的完整实现，包含装填、开枪、状态、帮助、走火开关、禁言等功能
使用统一的禁言工具模块
"""
import random
import asyncio
import datetime
import json
from pathlib import Path
from astrbot.api.all import *
from astrbot.api.event import filter
from utils.ban import BanUtils


class RouletteCommand:
    """俄罗斯轮盘指令功能类"""

    def __init__(self, plugin_instance):
        """
        初始化俄罗斯轮盘指令
        
        Args:
            plugin_instance: 主插件实例
        """
        self.plugin = plugin_instance
        self.logger = plugin_instance.logger
        
        # 游戏状态管理
        self.group_games = {}  # 群聊ID -> 游戏状态
        self.group_misfire = {}  # 群聊ID -> 是否开启走火
        self.timeout_tasks = {}  # 群聊ID -> 超时任务
        
        # 配置参数
        self.chamber_count = 6  # 弹膛数量
        self.timeout = 300  # 超时时间（秒）
        self.misfire_prob = 0.003  # 走火概率
        self.min_ban = 60  # 最小禁言时间
        self.max_ban = 300  # 最大禁言时间
        self.max_bullet_count = 6  # 最大子弹数量
        self.default_misfire = False  # 默认走火状态
        self.no_full_chamber = False  # 是否禁止满膛
        self.end_on_full_rotation = False  # 是否在完整轮转后结束
        self.hide_bullet_count = False  # 是否隐藏子弹数量
        
        # 数据持久化
        self.data_dir = Path("data/plugins/astrbot_plugin_rg")
        self.config_file = self.data_dir / "group_misfire.json"
        
        # 加载持久化配置
        self._load_misfire_config()

    def _get_group_id(self, event: AstrMessageEvent) -> int:
        """获取群ID"""
        return getattr(event.message_obj, "group_id", None)

    def _get_user_name(self, event: AstrMessageEvent) -> str:
        """获取用户昵称"""
        return event.get_sender_name() or "玩家"

    async def _is_group_admin(self, event: AstrMessageEvent) -> bool:
        """检查用户是否是群管理员"""
        try:
            group_id = self._get_group_id(event)
            if not group_id:
                return False

            user_id = int(event.get_sender_id())

            # 检查是否是bot超级管理员
            if event.is_admin():
                return True

            # 调用API获取群成员信息
            if hasattr(event.bot, "get_group_member_info"):
                member_info = await event.bot.get_group_member_info(
                    group_id=group_id, user_id=user_id, no_cache=True
                )

                # 检查角色：owner(群主) 或 admin(管理员)
                role = (
                    member_info.get("role", "")
                    if isinstance(member_info, dict)
                    else getattr(member_info, "role", "")
                )
                return role in ["owner", "admin"]

            return False
        except Exception as e:
            self.logger.error(f"检查群管理员权限失败: {e}")
            return False

    def _init_group(self, group_id: int):
        """初始化群状态"""
        if group_id not in self.group_misfire:
            self.group_misfire[group_id] = self.default_misfire

    def _load_misfire_config(self):
        """加载走火配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.group_misfire.update(data)
                self.logger.info(f"已加载 {len(data)} 个群的走火配置")
            else:
                self.logger.info("未找到走火配置文件，使用默认配置")
        except Exception as e:
            self.logger.error(f"加载走火配置失败: {e}")

    def _save_misfire_config(self):
        """保存走火配置"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.group_misfire, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"已保存 {len(self.group_misfire)} 个群的走火配置")
        except Exception as e:
            self.logger.error(f"保存走火配置失败: {e}")

    def _create_chambers(self, bullet_count: int) -> list[bool]:
        """创建弹膛状态"""
        chambers = [False] * self.chamber_count
        if bullet_count > 0:
            positions = random.sample(range(self.chamber_count), bullet_count)
            for pos in positions:
                chambers[pos] = True
        return chambers

    def _get_random_bullet_count(self) -> int:
        """获取随机子弹数量"""
        max_count = self.max_bullet_count
        if self.no_full_chamber and max_count > 1:
            max_count -= 1
        return random.randint(1, max_count)

    def _parse_bullet_count(self, message: str) -> int:
        """解析子弹数量"""
        parts = message.strip().split()
        if len(parts) < 2:
            return None

        try:
            count = int(parts[1])
            max_allowed = (
                self.chamber_count - 1 if self.no_full_chamber else self.chamber_count
            )
            if 1 <= count <= max_allowed:
                return count
        except (ValueError, IndexError):
            pass
        return None

    def _check_game_end(self, game: dict) -> bool:
        """检查游戏是否应该结束"""
        chambers = game.get("chambers", [])
        remaining = sum(chambers)

        if remaining == 0:
            return True

        if self.end_on_full_rotation:
            shot_count = game.get("shot_count", 0)
            remaining_chambers = self.chamber_count - (shot_count % self.chamber_count)
            if remaining == remaining_chambers:
                return True

        return False

    def _cleanup_game(self, group_id: int):
        """清理游戏状态和超时任务"""
        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]
        self.group_games.pop(group_id, None)

    async def _is_user_bannable(self, event: AstrMessageEvent, user_id: int) -> bool:
        """检查用户是否可以被禁言（不是群主或管理员）"""
        return await BanUtils.is_user_bannable(event, user_id, self.logger)

    def _format_ban_duration(self, seconds: int) -> str:
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

    async def _ban_user(self, event: AstrMessageEvent, user_id: int) -> int:
        """禁言用户 - 使用统一的禁言工具"""
        return await BanUtils.ban_user_random(event, user_id, self.min_ban, self.max_ban, self.logger)

    async def _is_group_admin(self, event: AstrMessageEvent) -> bool:
        """检查用户是否是群管理员"""
        try:
            group_id = self._get_group_id(event)
            if not group_id:
                return False

            user_id = int(event.get_sender_id())

            # 检查是否是bot超级管理员
            if event.is_admin():
                return True

            # 调用API获取群成员信息
            if hasattr(event.bot, "get_group_member_info"):
                member_info = await event.bot.get_group_member_info(
                    group_id=group_id, user_id=user_id, no_cache=True
                )

                # 检查角色：owner(群主) 或 admin(管理员)
                role = (
                    member_info.get("role", "")
                    if isinstance(member_info, dict)
                    else getattr(member_info, "role", "")
                )
                return role in ["owner", "admin"]

            return False
        except Exception as e:
            self.logger.error(f"检查群管理员权限失败: {e}")
            return False

    def _init_group(self, group_id: int):
        """初始化群状态"""
        if group_id not in self.group_misfire:
            self.group_misfire[group_id] = self.default_misfire

    def _load_misfire_config(self):
        """加载走火配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.group_misfire.update(data)
                self.logger.info(f"已加载 {len(data)} 个群的走火配置")
            else:
                self.logger.info("未找到走火配置文件，使用默认配置")
        except Exception as e:
            self.logger.error(f"加载走火配置失败: {e}")

    def _save_misfire_config(self):
        """保存走火配置"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.group_misfire, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"已保存 {len(self.group_misfire)} 个群的走火配置")
        except Exception as e:
            self.logger.error(f"保存走火配置失败: {e}")

    def _create_chambers(self, bullet_count: int) -> list[bool]:
        """创建弹膛状态"""
        chambers = [False] * self.chamber_count
        if bullet_count > 0:
            positions = random.sample(range(self.chamber_count), bullet_count)
            for pos in positions:
                chambers[pos] = True
        return chambers

    def _get_random_bullet_count(self) -> int:
        """获取随机子弹数量"""
        max_count = self.max_bullet_count
        if self.no_full_chamber and max_count > 1:
            max_count -= 1
        return random.randint(1, max_count)

    def _parse_bullet_count(self, message: str) -> int:
        """解析子弹数量"""
        parts = message.strip().split()
        if len(parts) < 2:
            return None

        try:
            count = int(parts[1])
            max_allowed = (
                self.chamber_count - 1 if self.no_full_chamber else self.chamber_count
            )
            if 1 <= count <= max_allowed:
                return count
        except (ValueError, IndexError):
            pass
        return None

    def _check_game_end(self, game: dict) -> bool:
        """检查游戏是否应该结束"""
        chambers = game.get("chambers", [])
        remaining = sum(chambers)

        if remaining == 0:
            return True

        if self.end_on_full_rotation:
            shot_count = game.get("shot_count", 0)
            remaining_chambers = self.chamber_count - (shot_count % self.chamber_count)
            if remaining == remaining_chambers:
                return True

        return False

    def _cleanup_game(self, group_id: int):
        """清理游戏状态和超时任务"""
        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]
        self.group_games.pop(group_id, None)

    async def _start_timeout(self, event: AstrMessageEvent, group_id: int):
        """启动超时机制"""
        # 取消之前的超时任务（如果存在）
        if group_id in self.timeout_tasks:
            task = self.timeout_tasks[group_id]
            if not task.done():
                task.cancel()

        # 保存必要的信息用于超时回调
        bot = event.bot

        # 创建新的超时任务
        async def timeout_check():
            try:
                await asyncio.sleep(self.timeout)
                # 检查游戏是否还在进行
                if group_id in self.group_games:
                    # 清理游戏状态
                    del self.group_games[group_id]

                    # 发送超时通知
                    try:
                        if hasattr(bot, "send_group_msg"):
                            await bot.send_group_msg(
                                group_id=group_id,
                                message=f"⏰ 游戏超时！\n⏱️ {self.timeout} 秒无人操作\n🏁 游戏已自动结束",
                            )
                    except Exception as e:
                        self.logger.error(f"发送超时通知失败: {e}")

                    self.logger.info(f"群 {group_id} 游戏因超时而结束")
            except asyncio.CancelledError:
                # 任务被取消，说明有新操作
                pass
            except Exception as e:
                self.logger.error(f"超时检查失败: {e}")

        # 启动超时任务
        self.timeout_tasks[group_id] = asyncio.create_task(timeout_check())
        self.logger.debug(f"群 {group_id} 超时任务已启动，{self.timeout} 秒后触发")

    def _check_misfire(self, group_id: int) -> bool:
        """检查是否触发随机走火"""
        if not self.group_misfire.get(group_id, False):
            return False
        return random.random() < self.misfire_prob

    # ========== 指令实现 ==========

    async def load_bullets_command(self, event: AstrMessageEvent):
        """装填子弹指令"""
        try:
            group_id = self._get_group_id(event)
            if not group_id:
                yield event.plain_result("❌ 仅限群聊使用")
                return

            self._init_group(group_id)
            user_name = self._get_user_name(event)

            # 检查是否已有游戏
            if group_id in self.group_games:
                yield event.plain_result(f"💥 {user_name}，游戏还在进行中！")
                return

            # 解析子弹数量
            bullet_count = self._parse_bullet_count(event.message_str or "")

            # 如果指定了子弹数量，检查是否是管理员
            if bullet_count is not None:
                if not await self._is_group_admin(event):
                    yield event.plain_result(
                        f"😏 {user_name}，你又不是管理才不听你的！\n💡 请使用 装填 进行随机装填"
                    )
                    return
            else:
                # 未指定数量，随机装填
                bullet_count = self._get_random_bullet_count()

            # 创建游戏
            chambers = self._create_chambers(bullet_count)
            self.group_games[group_id] = {
                "chambers": chambers,
                "current": 0,
                "start_time": datetime.datetime.now(),
                "shot_count": 0,
            }

            # 设置超时
            await self._start_timeout(event, group_id)

            self.logger.info(f"用户 {user_name} 在群 {group_id} 装填 {bullet_count} 发子弹")

            # 构建装填消息
            if self.hide_bullet_count:
                load_msg = f"{user_name} 装填了 ? 发子弹"
            else:
                load_msg = f"{user_name} 装填了 {bullet_count} 发子弹"
                
            yield event.plain_result(
                f"🔫 {load_msg}\n"
                f"💀 {self.chamber_count} 弹膛，生死一线！\n"
                f"⚡ 限时 {self.timeout} 秒！"
            )
        except Exception as e:
            self.logger.error(f"装填子弹失败: {e}")
            yield event.plain_result("❌ 装填失败，请重试")

    async def shoot_command(self, event: AstrMessageEvent):
        """开枪指令"""
        try:
            group_id = self._get_group_id(event)
            if not group_id:
                yield event.plain_result("❌ 仅限群聊使用")
                return

            self._init_group(group_id)
            user_name = self._get_user_name(event)
            user_id = int(event.get_sender_id())

            # 检查游戏状态
            game = self.group_games.get(group_id)
            if not game:
                yield event.plain_result(f"⚠️ {user_name}，枪里没子弹！")
                return

            # 重置超时
            await self._start_timeout(event, group_id)

            # 执行射击
            chambers = game["chambers"]
            current = game["current"]

            # 增加射击计数
            game["shot_count"] = game.get("shot_count", 0) + 1

            if chambers[current]:
                # 中弹
                self.logger.info(f"💥 用户 {user_name}({user_id}) 中弹！开始处理...")
                chambers[current] = False
                game["current"] = (current + 1) % self.chamber_count

                # 检查是否可禁言（管理员/群主免疫）
                self.logger.info(f"🔍 检查用户 {user_id} 是否可禁言...")
                bannable = await self._is_user_bannable(event, user_id)
                self.logger.info(f"🔍 用户 {user_id} 可禁言结果: {bannable}")
                
                if not bannable:
                    # 管理员/群主免疫
                    self.logger.info(f"⏭️ 用户 {user_name}({user_id}) 是管理员/群主，免疫中弹")
                    yield event.plain_result(
                        f"💥 枪声炸响！\n😱 {user_name} 中弹倒地！\n⚠️ 管理员/群主免疫！"
                    )
                else:
                    # 普通用户，执行禁言
                    self.logger.info(f"🎯 开始执行禁言流程 - 用户:{user_name}({user_id})")
                    ban_duration = await self._ban_user(event, user_id)
                    self.logger.info(f"🎯 禁言流程完成 - 返回时长:{ban_duration}")
                    
                    if ban_duration > 0:
                        formatted_duration = self._format_ban_duration(ban_duration)
                        ban_msg = f"🔇 禁言 {formatted_duration}"
                        self.logger.info(f"✅ 禁言成功消息: {ban_msg}")
                    else:
                        ban_msg = "⚠️ 禁言失败！"
                        self.logger.warning(f"❌ 禁言失败，返回时长为0")

                    self.logger.info(f"💥 用户 {user_name}({user_id}) 在群 {group_id} 中弹处理完成")

                    yield event.plain_result(
                        f"💥 枪声炸响！\n😱 {user_name} 中弹倒地！\n{ban_msg}"
                    )
            else:
                # 空弹
                game["current"] = (current + 1) % self.chamber_count
                self.logger.info(f"用户 {user_name}({user_id}) 在群 {group_id} 空弹逃生")
                yield event.plain_result(f"🍀 {user_name} 扣动扳机...咔嚓！空弹！")

            # 检查游戏结束条件
            if self._check_game_end(game):
                self._cleanup_game(group_id)
                self.logger.info(f"群 {group_id} 游戏结束")
                yield event.plain_result("🏁 游戏结束！所有子弹都已射完\n🔄 再来一局？")

        except Exception as e:
            self.logger.error(f"开枪失败: {e}")
            yield event.plain_result("❌ 操作失败，请重试")

    async def status_command(self, event: AstrMessageEvent):
        """查看游戏状态指令"""
        try:
            group_id = self._get_group_id(event)
            if not group_id:
                yield event.plain_result("❌ 仅限群聊使用")
                return

            game = self.group_games.get(group_id)
            if not game:
                yield event.plain_result(
                    "🔍 没有游戏进行中\n💡 使用 装填 开始游戏（随机装填）\n💡 管理员可使用 装填 [数量] 指定子弹"
                )
                return

            chambers = game["chambers"]
            current = game["current"]
            remaining = sum(chambers)

            status = "🎯 有子弹" if chambers[current] else "🍀 安全"

            yield event.plain_result(
                f"🔫 游戏进行中\n"
                f"📊 剩余子弹：{remaining}发\n"
                f"🎯 当前弹膛：第{current + 1}膛\n"
                f"{status}"
            )
        except Exception as e:
            self.logger.error(f"查询游戏状态失败: {e}")
            yield event.plain_result("❌ 查询失败，请重试")

    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息指令"""
        try:
            help_text = """🔫 左轮手枪对决 v1.0

【用户指令】
装填 - 随机装填子弹（1-6发）
开枪 - 扣动扳机
状态 - 查看游戏状态
帮助 - 显示帮助

【管理员指令】
装填 [数量] - 装填指定数量子弹（1-6发）
走火开 - 开启随机走火
走火关 - 关闭随机走火

【游戏规则】
• 6弹膛，随机装填指定数量子弹
• 中弹禁言60-300秒随机时长
• 超时300秒自动结束游戏
• 走火概率0.3%(如开启)
• 管理员/群主免疫禁言"""

            yield event.plain_result(help_text)
        except Exception as e:
            self.logger.error(f"显示帮助失败: {e}")
            yield event.plain_result("❌ 显示帮助失败")

    async def enable_misfire_command(self, event: AstrMessageEvent):
        """开启随机走火指令"""
        try:
            group_id = self._get_group_id(event)
            if not group_id:
                yield event.plain_result("❌ 仅限群聊使用")
                return

            # 检查群管理员权限
            if not await self._is_group_admin(event):
                user_name = self._get_user_name(event)
                yield event.plain_result(f"😏 {user_name}，你又不是管理才不听你的！")
                return

            self._init_group(group_id)
            self.group_misfire[group_id] = True
            self._save_misfire_config()
            self.logger.info(f"群 {group_id} 随机走火已开启")
            yield event.plain_result("🔥 随机走火已开启！")
        except Exception as e:
            self.logger.error(f"开启走火失败: {e}")
            yield event.plain_result("❌ 操作失败，请重试")

    async def disable_misfire_command(self, event: AstrMessageEvent):
        """关闭随机走火指令"""
        try:
            group_id = self._get_group_id(event)
            if not group_id:
                yield event.plain_result("❌ 仅限群聊使用")
                return

            # 检查群管理员权限
            if not await self._is_group_admin(event):
                user_name = self._get_user_name(event)
                yield event.plain_result(f"😏 {user_name}，你又不是管理才不听你的！")
                return

            self._init_group(group_id)
            self.group_misfire[group_id] = False
            self._save_misfire_config()
            self.logger.info(f"群 {group_id} 随机走火已关闭")
            yield event.plain_result("💤 随机走火已关闭！")
        except Exception as e:
            self.logger.error(f"关闭走火失败: {e}")
            yield event.plain_result("❌ 操作失败，请重试")

    async def check_misfire_for_message(self, event: AstrMessageEvent, message: str):
        """检查消息是否触发随机走火"""
        try:
            group_id = self._get_group_id(event)
            if not group_id or not self._check_misfire(group_id):
                return

            user_name = self._get_user_name(event)
            user_id = int(event.get_sender_id())

            # 检查是否可禁言（管理员/群主免疫）
            if not await self._is_user_bannable(event, user_id):
                # 管理员/群主免疫
                self.logger.info(f"⏭️ 群 {group_id} 用户 {user_name}({user_id}) 是管理员/群主，免疫随机走火")
                yield event.plain_result(
                    f"💥 手枪走火！\n😱 {user_name} 不幸中弹！\n⚠️ 管理员/群主免疫！"
                )
            else:
                # 普通用户，执行禁言
                ban_duration = await self._ban_user(event, user_id)
                if ban_duration > 0:
                    formatted_duration = self._format_ban_duration(ban_duration)
                    ban_msg = f"🔇 禁言 {formatted_duration}！"
                else:
                    ban_msg = "⚠️ 禁言失败！"

                self.logger.info(f"💥 群 {group_id} 用户 {user_name}({user_id}) 触发随机走火")

                yield event.plain_result(
                    f"💥 手枪走火！\n😱 {user_name} 不幸中弹！\n{ban_msg}"
                )
        except Exception as e:
            self.logger.error(f"随机走火检查失败: {e}")

    async def ban_test_command(self, event: AstrMessageEvent):
        """禁言测试指令 - 任何用户输入后会被禁言1分钟"""
        try:
            group_id = self._get_group_id(event)
            if not group_id:
                yield event.plain_result("❌ 仅限群聊使用")
                return

            user_id = int(event.get_sender_id())
            user_name = self._get_user_name(event)

            self.logger.info(f"🧪 用户 {user_name}({user_id}) 测试禁言功能")

            # 直接使用example.py的禁言逻辑，固定1分钟
            duration = 60
            formatted_duration = self._format_ban_duration(duration)

            try:
                if hasattr(event.bot, "set_group_ban"):
                    self.logger.info(f"🎯 正在禁言用户 {user_id}，时长 {formatted_duration}")
                    await event.bot.set_group_ban(
                        group_id=group_id, user_id=user_id, duration=duration
                    )
                    self.logger.info(f"✅ 用户 {user_id} 在群 {group_id} 被禁言 {formatted_duration}")
                    yield event.plain_result(f"✅ 禁言测试成功！你被禁言 {formatted_duration}")
                else:
                    self.logger.error("❌ Bot 没有 set_group_ban 方法，无法禁言")
                    yield event.plain_result("❌ Bot 没有 set_group_ban 方法，无法禁言")
            except Exception as e:
                self.logger.error(f"❌ 禁言用户失败: {e}")
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ["permission", "权限", "privilege", "insufficient"]):
                    yield event.plain_result("🔐 权限不足：请检查机器人是否有群管理权限！")
                else:
                    yield event.plain_result(f"❌ 禁言失败: {e}")
                
        except Exception as e:
            self.logger.error(f"禁言测试失败: {e}")
            yield event.plain_result("❌ 测试失败，请重试")