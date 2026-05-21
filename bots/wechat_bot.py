#!/usr/bin/env python3
"""
微信机器人 — 基于 Wechaty
"""

import asyncio
from pathlib import Path

from rich.console import Console

from bots.adapter import BotAdapter

console = Console()


class WechatBot(BotAdapter):
    """微信机器人（Wechaty）"""

    def __init__(self, config: dict, bot_config: dict,
                 persona_file: str, voice_dir: str, engine_name: str):
        super().__init__(config, bot_config, persona_file, voice_dir, engine_name)
        self.puppet_type = bot_config.get("puppet", "wechaty-puppet-padlocal")
        self.token = bot_config.get("token", "")
        self.bot = None

    async def start(self):
        """启动微信机器人"""
        console.print("[cyan]正在启动微信机器人...[/cyan]")

        if not self.token:
            console.print("[red]❌ 缺少 Wechaty puppet token[/red]")
            console.print("[yellow]请在 config.json 中配置 bots.wechat.token[/yellow]")
            console.print("[yellow]获取方式: https://github.com/wechaty/puppet-padlocal[/yellow]")
            return

        try:
            from wechaty import Wechaty, Contact, Message
            from wechaty_puppet import MessageType
        except ImportError:
            console.print("[red]❌ wechaty 未安装[/red]")
            console.print("[yellow]运行: pip install wechaty wechaty-puppet-padlocal[/yellow]")
            return

        # 设置环境变量
        import os
        os.environ["WECHATY_PUPPET"] = self.puppet_type
        os.environ["WECHATY_PUPPET_PADLOCAL_TOKEN"] = self.token

        self.bot = Wechaty()

        @self.bot.on("message")
        async def on_message(msg: Message):
            await self._handle_wechaty_message(msg)

        @self.bot.on("login")
        async def on_login(contact: Contact):
            console.print(f"[green]✅ 登录成功: {contact.name}[/green]")
            console.print("[green]🫀 赛博前任已上线，等待消息...[/green]")

        @self.bot.on("logout")
        async def on_logout(contact: Contact):
            console.print(f"[yellow]已登出: {contact.name}[/yellow]")

        await self.bot.start()
        console.print("[green]微信机器人已启动[/green]")

        # 保持运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.stop()

    async def _handle_wechaty_message(self, msg):
        """处理微信消息"""
        from wechaty import Message, MessageType

        # 只处理文本消息
        if msg.type() != MessageType.MESSAGE_TYPE_TEXT:
            return

        # 不处理自己发的消息
        if msg.is_self():
            return

        talker = msg.talker()
        room = msg.room()

        # 私聊
        if not room:
            chat_id = talker.contact_id
            sender = talker.name
            text = msg.text()

            console.print(f"[dim]收到 {sender}: {text}[/dim]")
            await self.handle_message(chat_id, sender, text)

        # 群聊（可选处理）
        # if room:
        #     room_id = room.room_id
        #     if msg.mention_self():
        #         text = msg.text()
        #         await self.handle_message(room_id, talker.name, text)

    async def stop(self):
        """停止机器人"""
        if self.bot:
            await self.bot.stop()
        console.print("[yellow]微信机器人已停止[/yellow]")

    async def send_text(self, chat_id: str, text: str):
        """发送文字消息"""
        if not self.bot:
            return

        try:
            from wechaty import Contact
            contact = self.bot.Contact.load(chat_id)
            await contact.say(text)
            console.print(f"[dim]已发送: {text[:50]}...[/dim]")
        except Exception as e:
            console.print(f"[red]发送失败: {e}[/red]")

    async def send_voice(self, chat_id: str, audio_path: Path):
        """发送语音消息"""
        if not self.bot:
            return

        try:
            from wechaty import Contact, FileBox

            # Wechaty 发送语音需要 silk 格式
            silk_path = await self._convert_to_silk(audio_path)
            if silk_path and silk_path.exists():
                file_box = FileBox.from_file(str(silk_path))
                contact = self.bot.Contact.load(chat_id)
                await contact.say(file_box)
                console.print(f"[dim]已发送语音: {silk_path.name}[/dim]")
        except Exception as e:
            console.print(f"[red]语音发送失败: {e}[/red]")

    async def _convert_to_silk(self, audio_path: Path) -> Path | None:
        """将 wav 转换为 silk 格式（微信语音格式）"""
        silk_path = audio_path.with_suffix(".silk")

        try:
            # 使用 pilk 库转换
            import pilk
            pilk.encode(str(audio_path), str(silk_path), pcm_rate=24000)
            return silk_path
        except ImportError:
            console.print("[yellow]pilk 未安装，无法转换 silk 格式[/yellow]")
            console.print("[yellow]运行: pip install pilk[/yellow]")

        # 备用方案：直接发送音频文件
        return audio_path
