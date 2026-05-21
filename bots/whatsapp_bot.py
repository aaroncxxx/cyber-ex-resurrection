#!/usr/bin/env python3
"""
WhatsApp 机器人 — 基于 Meta Cloud API
"""

import asyncio
import json
from pathlib import Path

import aiohttp
from rich.console import Console

from bots.adapter import BotAdapter

console = Console()


class WhatsAppBot(BotAdapter):
    """WhatsApp 机器人（Meta Cloud API）"""

    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, config: dict, bot_config: dict,
                 persona_file: str, voice_dir: str, engine_name: str):
        super().__init__(config, bot_config, persona_file, voice_dir, engine_name)
        self.phone_number_id = bot_config.get("phone_number_id", "")
        self.access_token = bot_config.get("access_token", "")
        self.verify_token = bot_config.get("verify_token", "")
        self.webhook_port = bot_config.get("webhook_port", 8080)

    async def start(self):
        """启动 WhatsApp 机器人"""
        console.print("[cyan]正在启动 WhatsApp 机器人...[/cyan]")

        if not self.phone_number_id or not self.access_token:
            console.print("[red]❌ 缺少 WhatsApp 配置[/red]")
            console.print("[yellow]请在 config.json 中配置:[/yellow]")
            console.print("[yellow]  bots.whatsapp.phone_number_id[/yellow]")
            console.print("[yellow]  bots.whatsapp.access_token[/yellow]")
            console.print("[yellow]获取方式: https://developers.facebook.com/docs/whatsapp[/yellow]")
            return

        console.print("[green]✅ WhatsApp 机器人已启动[/green]")
        console.print(f"[cyan]Webhook 监听端口: {self.webhook_port}[/cyan]")
        console.print("[green]🫀 赛博前任已上线，等待消息...[/green]")

        # 启动 webhook 服务器
        await self._start_webhook()

    async def _start_webhook(self):
        """启动 webhook 服务器"""
        from aiohttp import web

        app = web.Application()
        app.router.add_get("/webhook", self._verify_webhook)
        app.router.add_post("/webhook", self._handle_webhook)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.webhook_port)
        await site.start()

        console.print(f"[green]Webhook 服务器已启动: http://0.0.0.0:{self.webhook_port}/webhook[/green]")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await runner.cleanup()

    async def _verify_webhook(self, request):
        """验证 webhook（Meta 要求）"""
        from aiohttp import web

        mode = request.query.get("hub.mode")
        token = request.query.get("hub.verify_token")
        challenge = request.query.get("hub.challenge")

        if mode == "subscribe" and token == self.verify_token:
            console.print("[green]Webhook 验证成功[/green]")
            return web.Response(text=challenge)
        else:
            return web.Response(status=403)

    async def _handle_webhook(self, request):
        """处理 webhook 消息"""
        from aiohttp import web

        data = await request.json()

        try:
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            for msg in messages:
                if msg.get("type") == "text":
                    from_id = msg["from"]
                    text = msg["text"]["body"]
                    sender_name = value.get("contacts", [{}])[0].get("profile", {}).get("name", from_id)

                    console.print(f"[dim]收到 {sender_name}: {text}[/dim]")
                    await self.handle_message(from_id, sender_name, text)

        except Exception as e:
            console.print(f"[red]处理消息失败: {e}[/red]")

        return web.Response(status=200)

    async def stop(self):
        """停止机器人"""
        console.print("[yellow]WhatsApp 机器人已停止[/yellow]")

    async def send_text(self, chat_id: str, text: str):
        """发送文字消息"""
        url = f"{self.API_BASE}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": chat_id,
            "type": "text",
            "text": {"body": text}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    console.print(f"[dim]已发送: {text[:50]}...[/dim]")
                else:
                    error = await resp.json()
                    console.print(f"[red]发送失败: {error}[/red]")

    async def send_voice(self, chat_id: str, audio_path: Path):
        """发送语音消息"""
        # WhatsApp 需要先上传媒体文件
        media_id = await self._upload_media(audio_path, "audio/ogg")
        if not media_id:
            await self.send_text(chat_id, "[语音消息]")
            return

        url = f"{self.API_BASE}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": chat_id,
            "type": "audio",
            "audio": {"id": media_id}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    console.print(f"[dim]已发送语音: {audio_path.name}[/dim]")
                else:
                    error = await resp.json()
                    console.print(f"[red]语音发送失败: {error}[/red]")

    async def _upload_media(self, file_path: Path, mime_type: str) -> str | None:
        """上传媒体文件到 WhatsApp"""
        url = f"{self.API_BASE}/{self.phone_number_id}/media"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        data = aiohttp.FormData()
        data.add_field("file", open(str(file_path), "rb"), filename=file_path.name, content_type=mime_type)
        data.add_field("messaging_product", "whatsapp")
        data.add_field("type", mime_type)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("id")

        return None
