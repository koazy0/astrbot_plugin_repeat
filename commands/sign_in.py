"""
签到功能模块
"""
import json
import os
from datetime import datetime, date
from commands.base import BaseFeature
from typing import Generator, Optional
from astrbot.api.all import *


class SignInFeature(BaseFeature):
    """签到功能 - 支持 /sign 命令"""

    def __init__(self):
        super().__init__(
            name="sign_in",
            description="每日签到功能"
        )
        self.command = "/sign"
        self.data_file = "data/plugins/astrbot_plugin_rg/sign_in_data.json"
        self.sign_data = self._load_sign_data()

    def _load_sign_data(self):
        """加载签到数据"""
        if not os.path.exists(self.data_file):
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _save_sign_data(self):
        """保存签到数据"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.sign_data, f, ensure_ascii=False, indent=2)

    def _get_today(self):
        """获取今日日期字符串"""
        return date.today().strftime("%Y-%m-%d")

    async def can_handle(self, message: str) -> bool:
        """判断是否能处理 - 匹配 /sign 命令"""
        return message == self.command

    async def handle(self, event: AstrMessageEvent, message: str, sender_name: str) -> Optional[Generator]:
        """处理签到"""
        user_id = event.get_sender_id()
        group_id = event.message_obj.group_id
        today = self._get_today()

        # 初始化用户数据
        user_key = f"{group_id}_{user_id}"
        if user_key not in self.sign_data:
            self.sign_data[user_key] = {
                "total_days": 0,
                "last_sign_date": None,
                "continuous_days": 0
            }

        user_data = self.sign_data[user_key]

        # 检查今天是否已签到
        if user_data["last_sign_date"] == today:
            yield event.plain_result(f"📅 {sender_name}，你今天已经签到过了！")
            return

        # 处理连续签到
        yesterday = (date.today().replace(day=date.today().day - 1)).strftime("%Y-%m-%d")
        if user_data["last_sign_date"] == yesterday:
            user_data["continuous_days"] += 1
        else:
            user_data["continuous_days"] = 1

        # 更新签到数据
        user_data["total_days"] += 1
        user_data["last_sign_date"] = today
        self._save_sign_data()

        # 计算奖励（示例）
        reward = self._calculate_reward(user_data["continuous_days"])

        # 返回签到成功消息
        yield event.plain_result(
            f"🎉 {sender_name} 签到成功！\n"
            f"📊 连续签到：{user_data['continuous_days']} 天\n"
            f"📈 累计签到：{user_data['total_days']} 天\n"
            f"🎁 本次奖励：{reward}"
        )

    def _calculate_reward(self, continuous_days: int) -> str:
        """计算签到奖励"""
        base_coins = 10
        bonus = min(continuous_days, 7) * 2  # 最多连续7天有额外奖励
        return f"{base_coins + bonus} 金币"
