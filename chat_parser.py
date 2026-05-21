#!/usr/bin/env python3
"""
对话解析器 — 散乱文字 → 结构化聊天记录
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console

console = Console()


class ChatParser:
    """对话结构化解析器"""

    def __init__(self, config: dict):
        self.config = config

    def load_raw(self, chat_file: Path) -> list[dict]:
        """加载原始聊天记录"""
        with open(chat_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def dedup(self, messages: list[dict]) -> list[dict]:
        """去重（同一条消息可能在多张截图中出现）"""
        seen = set()
        unique = []
        for msg in messages:
            key = (msg.get("role", ""), msg.get("text", ""))
            if key not in seen:
                seen.add(key)
                unique.append(msg)
        return unique

    def merge_role(self, messages: list[dict]) -> list[dict]:
        """合并连续同一角色的消息"""
        if not messages:
            return []

        merged = []
        current = messages[0].copy()

        for msg in messages[1:]:
            if msg.get("role") == current.get("role"):
                # 合并文本
                current["text"] = current.get("text", "") + "\n" + msg.get("text", "")
            else:
                merged.append(current)
                current = msg.copy()

        merged.append(current)
        return merged

    def normalize(self, messages: list[dict]) -> list[dict]:
        """规范化消息格式"""
        normalized = []
        for msg in messages:
            norm = {
                "role": msg.get("role", "unknown"),
                "text": self._clean_text(msg.get("text", "")),
            }
            if msg.get("time"):
                norm["time"] = msg["time"]
            if msg.get("source"):
                norm["source"] = msg["source"]
            if norm["text"]:
                normalized.append(norm)
        return normalized

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        text = text.strip()
        # 移除多余空白
        text = re.sub(r"\s+", " ", text)
        return text

    def parse(self, chat_file: Path) -> list[dict]:
        """完整解析流程"""
        raw = self.load_raw(chat_file)
        console.print(f"[cyan]原始消息: {len(raw)} 条[/cyan]")

        deduped = self.dedup(raw)
        console.print(f"[cyan]去重后: {len(deduped)} 条[/cyan]")

        normalized = self.normalize(deduped)
        console.print(f"[cyan]规范化后: {len(normalized)} 条[/cyan]")

        merged = self.merge_role(normalized)
        console.print(f"[cyan]合并后: {len(merged)} 条[/cyan]")

        return merged

    def export(self, messages: list[dict], output_path: Path, format: str = "json"):
        """导出解析结果"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        elif format == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                for msg in messages:
                    role = "我" if msg["role"] == "me" else "TA"
                    f.write(f"[{role}] {msg['text']}\n")
        elif format == "md":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# 聊天记录\n\n")
                for msg in messages:
                    role = "**我**" if msg["role"] == "me" else "**TA**"
                    f.write(f"{role}: {msg['text']}\n\n")

        console.print(f"[green]已导出: {output_path}[/green]")
