#!/usr/bin/env python3
"""
QQ 机器人 — 基于 QQ 开放平台 Bot API
"""

import asyncio
import json
from pathlib import Path

from rich.console import Console

from bots.adapter import BotAdapter

console = Console()


class QQBot(BotAdapter):
    """QQ 机器人（QQ 开放平台）"""

    def __init__(self, config: dict, bot_config: dict,
                 persona_file: str, voice_dir: str, engine_name: str):
        super().__init__(config, bot_config, persona_file, voice_dir, engine_name)
        self.app_id = bot_config.get("app_id", "")
        self.app_secret = bot_config.get("app_secret", "")
        self.token = bot_config.get("token", "")
        self.client = None

    async def start(self):
        """启动 QQ 机器人"""
        console.print("[cyan]正在启动 QQ 机器人...[/cyan]")

        if not self.app_id or not self.token:
            console.print("[red]❌ 缺少 QQ 机器人配置[/red]")
            console.print("[yellow]请在 config.json 中配置 bots.qq.app_id 和 bots.qq.token[/yellow]")
            console.print("[yellow]获取方式: https://bot.q.qq.com/[/yellow]")
            return

        try:
            import qqbot
            from qqbot import QQBotClient, Intents
        except ImportError:
            console.print("[red]❌ qq-botpy 未安装[/red]")
            console.print("[yellow]运行: pip install qq-botpy[/yellow]")
            return

        # 创建客户端
        intents = Intents(
            public_guild_messages=True,
            public_messages=True,
        )

        self.client = QQBotClient(
            app_id=self.app_id,
            app_secret=self.app_secret,
            intents=intents,
            is_sandbox=False
        )

        @self.client.on_message_create
        async def on_message(message):
            await self._handle_qq_message(message)

        @self.client.on_ready
        async def on_ready(event):
            console.print("[green]✅ QQ 机器人已连接[/green]")
            console.print("[green]🫀 赛博前任已上线，等待消息...[/green]")

        try:
            await self.client.start(self.token)
        except KeyboardInterrupt:
            await self.stop()

    async def _handle_qq_message(self, message):
        """处理 QQ 消息"""
        # 忽略机器人自己的消息
        if message.author.bot:
            return

        chat_id = message.channel_id
        sender = message.author.username
        text = message.content

        console.print(f"[dim]收到 {sender}: {text}[/dim]")
        await self.handle_message(chat_id, sender, text)

    async def stop(self):
        """停止机器人"""
        if self.client:
            await self.client.close()
        console.print("[yellow]QQ 机器人已停止[/yellow]")

    async def send_text(self, chat_id: str, text: str):
        """发送文字消息"""
        if not self.client:
            return

        try:
            from qqbot import MessageCreateRequest
            request = MessageCreateRequest(content=text)
            await self.client.post_message(channel_id=chat_id, msg_id="", request=request)
            console.print(f"[dim]已发送: {text[:50]}...[/dim]")
        except Exception as e:
            console.print(f"[red]发送失败: {e}[/red]")

    async def send_voice(self, chat_id: str, audio_path: Path):
        """发送语音消息（QQ 不直接支持语音，发送文件）"""
        if not self.client:
            return

        try:
            from qqbot import FileCreateRequest
            request = FileCreateRequest(
                file_type=3,  # 音频
                url=str(audio_path),
                srv_send_msg=True
            )
            await self.client.post_file(channel_id=chat_id, request=request)
            console.print(f"[dim]已发送语音: {audio_path.name}[/dim]")
        except Exception as e:
            console.print(f"[red]语音发送失败: {e}[/red]")
            # Fallback: 发送文字提示
            await self.send_text(chat_id, "[语音消息]")
