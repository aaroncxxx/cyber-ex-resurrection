#!/usr/bin/env python3
"""
OCR 截图提取 — 使用 MIMO Omni 多模态模型识别聊天截图
"""

import base64
import json
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress

console = Console()

DEFAULT_OCR_PROMPT = """请识别这张聊天截图中的所有对话内容。

要求：
1. 识别每条消息的发送者（区分"我"和"对方"）
2. 提取消息文本内容
3. 如果有时间戳，提取时间
4. 如果有表情包/图片/语音消息，标注为 [表情]、[图片]、[语音]
5. 按时间顺序排列

输出 JSON 数组格式：
[
  {"role": "me" 或 "ex", "text": "消息内容", "time": "时间（如有）"},
  ...
]

只输出 JSON，不要其他文字。"""


class OCRExtractor:
    """聊天截图 OCR 提取器"""

    def __init__(self, config: dict):
        self.config = config
        self.mimo_config = config.get("mimo", {})

    def _call_mimo_omni(self, image_path: Path, prompt: str) -> str:
        """调用 MIMO Omni 模型识别图片"""
        # 使用 mimo_api.sh 脚本
        script_path = Path.home() / ".openclaw" / "skills" / "mimo-omni" / "mimo_api.sh"

        if script_path.exists():
            try:
                result = subprocess.run(
                    ["bash", str(script_path), "image", str(image_path), prompt],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception as e:
                console.print(f"[yellow]MIMO Omni 调用失败: {e}[/yellow]")

        # Fallback: 直接用 base64 + HTTP API
        return self._call_api_direct(image_path, prompt)

    def _call_api_direct(self, image_path: Path, prompt: str) -> str:
        """直接调用 API（备用方案）"""
        import aiohttp
        import asyncio

        api_key = self.mimo_config.get("api_key", "")
        endpoint = self.mimo_config.get("endpoint", "")

        if not api_key or not endpoint:
            raise ValueError("MIMO API 配置缺失，请在 config.json 中配置 mimo.api_key 和 mimo.endpoint")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = image_path.suffix.lower().lstrip(".")
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime = mime_map.get(f".{ext}", "image/png")

        payload = {
            "model": "mimo-v2.5-pro",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}}
                    ]
                }
            ]
        }

        async def _fetch():
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]

        return asyncio.run(_fetch())

    def _parse_messages(self, raw_text: str) -> list[dict]:
        """解析 OCR 输出为结构化消息"""
        # 尝试提取 JSON
        text = raw_text.strip()

        # 处理 markdown 代码块
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.startswith("```") and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        try:
            messages = json.loads(text)
            if isinstance(messages, list):
                return messages
        except json.JSONDecodeError:
            pass

        # 如果 JSON 解析失败，尝试逐行解析
        messages = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 尝试匹配常见格式
            for prefix in ["我:", "我：", "Me:", "对方:", "对方：", "TA:", "Ex:"]:
                if line.startswith(prefix):
                    role = "me" if prefix in ("我:", "我：", "Me:") else "ex"
                    msg_text = line[len(prefix):].strip()
                    if msg_text:
                        messages.append({"role": role, "text": msg_text})
                    break

        return messages

    async def extract_single(self, image_path: Path, prompt: Optional[str] = None) -> list[dict]:
        """提取单张截图的对话"""
        prompt = prompt or DEFAULT_OCR_PROMPT
        console.print(f"[cyan]处理: {image_path.name}[/cyan]")

        raw = self._call_mimo_omni(image_path, prompt)
        messages = self._parse_messages(raw)

        # 标注来源截图
        for msg in messages:
            msg["source"] = image_path.name

        return messages

    async def extract_all(self, image_paths: list[Path], prompt: Optional[str] = None) -> list[dict]:
        """提取所有截图的对话"""
        all_messages = []

        with Progress() as progress:
            task = progress.add_task("[cyan]OCR 提取中...", total=len(image_paths))

            for img_path in image_paths:
                try:
                    messages = await self.extract_single(img_path, prompt)
                    all_messages.extend(messages)
                    console.print(f"  [green]✓ {img_path.name}: {len(messages)} 条消息[/green]")
                except Exception as e:
                    console.print(f"  [red]✗ {img_path.name}: {e}[/red]")
                progress.advance(task)

        return all_messages
