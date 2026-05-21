#!/usr/bin/env python3
"""
飞书机器人 — 基于飞书开放平台
"""

import asyncio
import json
from pathlib import Path

from rich.console import Console

from bots.adapter import BotAdapter

console = Console()


class FeishuBot(BotAdapter):
    """飞书机器人"""

    def __init__(self, config: dict, bot_config: dict,
                 persona_file: str, voice_dir: str, engine_name: str):
        super().__init__(config, bot_config, persona_file, voice_dir, engine_name)
        self.app_id = bot_config.get("app_id", "")
        self.app_secret = bot_config.get("app_secret", "")
        self.verification_token = bot_config.get("verification_token", "")
        self.app = None
        self.tenant_token = None

    async def start(self):
        """启动飞书机器人"""
        console.print("[cyan]正在启动飞书机器人...[/cyan]")

        if not self.app_id or not self.app_secret:
            console.print("[red]❌ 缺少飞书机器人配置[/red]")
            console.print("[yellow]请在 config.json 中配置 bots.feishu.app_id 和 bots.feishu.app_secret[/yellow]")
            console.print("[yellow]获取方式: https://open.feishu.cn/[/yellow]")
            return

        try:
            import lark_oapi as lark
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
        except ImportError:
            console.print("[red]❌ lark-oapi 未安装[/red]")
            console.print("[yellow]运行: pip install lark-oapi[/yellow]")
            return

        # 创建客户端
        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .build()

        console.print("[green]✅ 飞书机器人已连接[/green]")
        console.print("[green]🫀 赛博前任已上线，等待消息...[/green]")

        # 飞书机器人使用 webhook 模式或长连接
        # 这里使用长连接模式
        try:
            import lark_oapi as lark
            from lark_oapi.adapter.fastapi import FastApiAdapter

            # 创建事件处理器
            handler = lark.EventDispatcherHandler.builder(
                self.verification_token, ""
            ).register_p2_im_message_receive_v1(
                self._handle_feishu_event
            ).build()

            # 启动长连接
            cli = lark.ws.Client(
                self.app_id,
                self.app_secret,
                event_handler=handler,
                log_level=lark.LogLevel.DEBUG
            )
            cli.start()

        except Exception as e:
            console.print(f"[red]飞书机器人启动失败: {e}[/red]")
            console.print("[yellow]提示: 飞书机器人需要配置事件订阅 URL[/yellow]")

    async def _handle_feishu_event(self, event):
        """处理飞书消息事件"""
        try:
            message = event.event.message
            sender = event.event.sender

            if message.message_type != "text":
                return

            content = json.loads(message.content)
            text = content.get("text", "")
            chat_id = message.chat_id
            sender_name = sender.sender_id.open_id

            console.print(f"[dim]收到消息: {text}[/dim]")
            await self.handle_message(chat_id, sender_name, text)

        except Exception as e:
            console.print(f"[red]处理飞书消息失败: {e}[/red]")

    async def stop(self):
        """停止机器人"""
        console.print("[yellow]飞书机器人已停止[/yellow]")

    async def send_text(self, chat_id: str, text: str):
        """发送文字消息"""
        try:
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

            body = CreateMessageRequestBody.builder() \
                .receive_id(chat_id) \
                .msg_type("text") \
                .content(json.dumps({"text": text})) \
                .build()

            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(body) \
                .build()

            response = self.client.im.v1.message.create(request)

            if response.success():
                console.print(f"[dim]已发送: {text[:50]}...[/dim]")
            else:
                console.print(f"[red]发送失败: {response.msg}[/red]")

        except Exception as e:
            console.print(f"[red]发送失败: {e}[/red]")

    async def send_voice(self, chat_id: str, audio_path: Path):
        """发送语音消息"""
        try:
            # 飞书需要先上传文件获取 file_key
            file_key = await self._upload_file(audio_path, "audio")
            if file_key:
                from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

                body = CreateMessageRequestBody.builder() \
                    .receive_id(chat_id) \
                    .msg_type("audio") \
                    .content(json.dumps({"file_key": file_key})) \
                    .build()

                request = CreateMessageRequest.builder() \
                    .receive_id_type("chat_id") \
                    .request_body(body) \
                    .build()

                self.client.im.v1.message.create(request)
                console.print(f"[dim]已发送语音: {audio_path.name}[/dim]")

        except Exception as e:
            console.print(f"[red]语音发送失败: {e}[/red]")
            await self.send_text(chat_id, "[语音消息]")

    async def _upload_file(self, file_path: Path, file_type: str) -> str | None:
        """上传文件到飞书"""
        try:
            from lark_oapi.api.im.v1 import CreateFileRequest, CreateFileRequestBody

            body = CreateFileRequestBody.builder() \
                .file_type(file_type) \
                .file_name(file_path.name) \
                .file(open(str(file_path), "rb")) \
                .build()

            request = CreateFileRequest.builder() \
                .request_body(body) \
                .build()

            response = self.client.im.v1.file.create(request)
            if response.success():
                return response.data.file_key

        except Exception as e:
            console.print(f"[red]文件上传失败: {e}[/red]")

        return None
