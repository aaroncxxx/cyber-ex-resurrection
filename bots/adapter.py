#!/usr/bin/env python3
"""
IM 机器人适配器基类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class BotAdapter(ABC):
    """IM 机器人适配器基类"""

    def __init__(self, config: dict, bot_config: dict,
                 persona_file: str, voice_dir: str, engine_name: str):
        self.config = config
        self.bot_config = bot_config
        self.persona_file = persona_file
        self.voice_dir = voice_dir
        self.engine_name = engine_name
        self._chat_engine = None

    def _get_chat_engine(self):
        """延迟加载对话引擎"""
        if self._chat_engine is None:
            from chat_engine import ChatEngine
            self._chat_engine = ChatEngine(
                self.config,
                self.persona_file,
                self.voice_dir,
                self.engine_name,
                enable_voice=self.bot_config.get("auto_voice", True)
            )
        return self._chat_engine

    @abstractmethod
    async def start(self):
        """启动机器人"""
        pass

    @abstractmethod
    async def stop(self):
        """停止机器人"""
        pass

    @abstractmethod
    async def send_text(self, chat_id: str, text: str):
        """发送文字消息"""
        pass

    @abstractmethod
    async def send_voice(self, chat_id: str, audio_path: Path):
        """发送语音消息"""
        pass

    async def on_message(self, chat_id: str, sender: str, text: str) -> dict:
        """
        处理收到的消息

        Returns:
            {"text": "回复", "voice_path": "语音路径(可选)"}
        """
        engine = self._get_chat_engine()

        # 添加上下文标记
        context_text = text
        if sender:
            context_text = f"[{sender}说] {text}"

        response = await engine.chat(context_text)
        return response

    async def handle_message(self, chat_id: str, sender: str, text: str):
        """完整的消息处理流程：生成回复 → 发送"""
        try:
            response = await self.on_message(chat_id, sender, text)

            # 发送文字
            if response.get("text"):
                await self.send_text(chat_id, response["text"])

            # 发送语音
            if response.get("voice_path"):
                voice_path = Path(response["voice_path"])
                if voice_path.exists() and voice_path.stat().st_size > 0:
                    await self.send_voice(chat_id, voice_path)

        except Exception as e:
            console.print(f"[red]消息处理失败: {e}[/red]")
            await self.send_text(chat_id, "啊...我突然不知道说什么了")


def get_bot(platform: str):
    """获取机器人适配器类"""
    if platform == "wechat":
        from bots.wechat_bot import WechatBot
        return WechatBot
    elif platform == "qq":
        from bots.qq_bot import QQBot
        return QQBot
    elif platform == "feishu":
        from bots.feishu_bot import FeishuBot
        return FeishuBot
    elif platform == "whatsapp":
        from bots.whatsapp_bot import WhatsAppBot
        return WhatsAppBot
    else:
        raise ValueError(f"不支持的平台: {platform}")
