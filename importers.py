#!/usr/bin/env python3
"""
多格式聊天记录导入 — txt / csv / html / 手机备份
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console

console = Console()


class ChatImporter:
    """聊天记录导入器"""

    @staticmethod
    def detect_format(file_path: Path) -> str:
        """自动检测文件格式"""
        suffix = file_path.suffix.lower()
        if suffix == ".json":
            return "json"
        elif suffix == ".csv":
            return "csv"
        elif suffix in (".html", ".htm"):
            return "html"
        elif suffix == ".txt":
            # 尝试判断 txt 格式类型
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(2000)
            if "-----" in head or "─────" in head:
                return "wechat_export"
            elif re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}", head):
                return "txt_timestamped"
            else:
                return "txt_plain"
        elif suffix in (".bak", ".db"):
            return "backup"
        else:
            return "unknown"

    @classmethod
    def import_file(cls, file_path: Path, format: str = None) -> list[dict]:
        """导入聊天记录文件，统一输出为 [{role, text, time, source}]"""
        format = format or cls.detect_format(file_path)
        console.print(f"[cyan]导入 {file_path.name} (格式: {format})[/cyan]")

        importers = {
            "json": cls._import_json,
            "csv": cls._import_csv,
            "html": cls._import_html,
            "wechat_export": cls._import_wechat_txt,
            "txt_timestamped": cls._import_txt_timestamped,
            "txt_plain": cls._import_txt_plain,
            "backup": cls._import_backup,
        }

        importer = importers.get(format)
        if not importer:
            console.print(f"[red]不支持的格式: {format}[/red]")
            return []

        messages = importer(file_path)

        # 添加来源标记
        for msg in messages:
            msg["source"] = file_path.name
            msg["import_format"] = format

        console.print(f"[green]✓ 导入 {len(messages)} 条消息[/green]")
        return messages

    @classmethod
    def import_directory(cls, dir_path: Path) -> list[dict]:
        """导入目录下所有聊天记录文件"""
        supported = (".json", ".csv", ".html", ".htm", ".txt", ".bak")
        files = sorted([
            f for f in dir_path.rglob("*")
            if f.is_file() and f.suffix.lower() in supported
        ])

        if not files:
            console.print("[yellow]未找到可导入的文件[/yellow]")
            return []

        console.print(f"[cyan]找到 {len(files)} 个文件[/cyan]")

        all_messages = []
        for f in files:
            try:
                messages = cls.import_file(f)
                all_messages.extend(messages)
            except Exception as e:
                console.print(f"[red]导入失败 {f.name}: {e}[/red]")

        # 按时间排序（如果有时间戳）
        all_messages.sort(key=lambda m: m.get("time", ""))

        console.print(f"[green]✅ 共导入 {len(all_messages)} 条消息[/green]")
        return all_messages

    # ─────────────────────────────────────────────
    # 各格式导入实现
    # ─────────────────────────────────────────────

    @staticmethod
    def _import_json(file_path: Path) -> list[dict]:
        """导入 JSON 格式"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # 可能是 {messages: [...]} 或其他结构
            for key in ("messages", "data", "records", "chat"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return []

    @staticmethod
    def _import_csv(file_path: Path) -> list[dict]:
        """导入 CSV 格式"""
        messages = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            # 检测是否有标题行
            sample = f.read(1024)
            f.seek(0)

            has_header = any(kw in sample.lower() for kw in ["role", "sender", "message", "content", "text", "发送者", "消息"])

            reader = csv.DictReader(f) if has_header else csv.reader(f)

            if has_header:
                for row in reader:
                    msg = {}
                    # 自动映射字段
                    for key, val in row.items():
                        key_lower = key.lower().strip()
                        if key_lower in ("role", "sender", "发送者", "from", "用户"):
                            msg["role"] = cls._normalize_role(val)
                        elif key_lower in ("text", "content", "message", "消息", "内容", "msg"):
                            msg["text"] = val.strip()
                        elif key_lower in ("time", "timestamp", "date", "时间", "日期"):
                            msg["time"] = val.strip()
                    if msg.get("text"):
                        messages.append(msg)
            else:
                for row in reader:
                    if len(row) >= 2:
                        messages.append({
                            "role": cls._normalize_role(row[0]),
                            "text": row[1].strip(),
                            "time": row[2].strip() if len(row) > 2 else "",
                        })

        return messages

    @staticmethod
    def _import_html(file_path: Path) -> list[dict]:
        """导入 HTML 格式（微信导出等）"""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        messages = []

        # 微信 HTML 导出格式
        # 通常结构: <div class="chat_item"><div class="nickname">...</div><div class="plain">...</div></div>
        chat_items = re.findall(
            r'class=["\'](?:chat_item|message)[\'"][^>]*>(.*?)</div>\s*</div>',
            content, re.DOTALL
        )

        for item in chat_items:
            # 提取发送者
            role_match = re.search(r'class=["\']nickname[\'"][^>]*>(.*?)</', item)
            role = cls._normalize_role(role_match.group(1)) if role_match else "unknown"

            # 提取消息内容
            text_match = re.search(r'class=["\'](?:plain|content|text)[\'"][^>]*>(.*?)</', item, re.DOTALL)
            text = text_match.group(1).strip() if text_match else ""

            # 清理 HTML 标签
            text = re.sub(r'<[^>]+>', '', text).strip()
            text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

            if text:
                messages.append({"role": role, "text": text})

        # 通用 HTML fallback
        if not messages:
            # 尝试解析 <p> 或 <div> 中的对话
            paragraphs = re.findall(r'<(?:p|div)[^>]*>(.*?)</(?:p|div)>', content, re.DOTALL)
            for p in paragraphs:
                text = re.sub(r'<[^>]+>', '', p).strip()
                text = text.replace('&nbsp;', ' ')
                if text and len(text) > 1:
                    # 尝试识别 "我:" 或 "对方:" 格式
                    role_match = re.match(r'^(我|对方|TA|Me|Ex)[：:]\s*(.+)', text)
                    if role_match:
                        messages.append({
                            "role": cls._normalize_role(role_match.group(1)),
                            "text": role_match.group(2).strip(),
                        })
                    else:
                        messages.append({"role": "unknown", "text": text})

        return messages

    @staticmethod
    def _import_wechat_txt(file_path: Path) -> list[dict]:
        """导入微信导出的 txt 格式（带分隔线）"""
        messages = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        current_role = None
        current_text = []
        current_time = ""

        for line in lines:
            line = line.rstrip()

            # 检测时间行: 2024-01-15 14:30:22
            time_match = re.match(r'^(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)', line)
            if time_match:
                # 保存上一条消息
                if current_role and current_text:
                    messages.append({
                        "role": current_role,
                        "text": "\n".join(current_text).strip(),
                        "time": current_time,
                    })
                current_time = time_match.group(1)
                current_text = []
                # 同一行可能有发送者
                rest = line[time_match.end():].strip()
                if rest:
                    current_text.append(rest)
                continue

            # 检测发送者行: 我 14:30:22 或 对方昵称 14:30:22
            sender_match = re.match(r'^(.+?)\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*$', line)
            if sender_match:
                # 保存上一条消息
                if current_role and current_text:
                    messages.append({
                        "role": current_role,
                        "text": "\n".join(current_text).strip(),
                        "time": current_time,
                    })
                current_role = cls._normalize_role(sender_match.group(1))
                current_time = sender_match.group(2)
                current_text = []
                continue

            # 分隔线
            if re.match(r'^[-─═]{4,}$', line):
                continue

            # 消息内容
            if line.strip():
                current_text.append(line)

        # 保存最后一条
        if current_role and current_text:
            messages.append({
                "role": current_role,
                "text": "\n".join(current_text).strip(),
                "time": current_time,
            })

        return messages

    @staticmethod
    def _import_txt_timestamped(file_path: Path) -> list[dict]:
        """导入带时间戳的 txt 格式"""
        messages = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 格式: [2024-01-15 14:30] 我: 消息内容
                match = re.match(
                    r'[\[（](\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)[\]）]\s*(.+?)[：:]\s*(.+)',
                    line
                )
                if match:
                    messages.append({
                        "time": match.group(1),
                        "role": cls._normalize_role(match.group(2)),
                        "text": match.group(3).strip(),
                    })
                    continue

                # 格式: 我: 消息内容 (无时间)
                match = re.match(r'^(.+?)[：:]\s*(.+)', line)
                if match:
                    messages.append({
                        "role": cls._normalize_role(match.group(1)),
                        "text": match.group(2).strip(),
                    })

        return messages

    @staticmethod
    def _import_txt_plain(file_path: Path) -> list[dict]:
        """导入纯文本格式（每行一条消息，交替角色）"""
        messages = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f if l.strip()]

        # 假设交替出现: 我, 对方, 我, 对方...
        roles = ["me", "ex"]
        for i, line in enumerate(lines):
            messages.append({
                "role": roles[i % 2],
                "text": line,
            })

        return messages

    @staticmethod
    def _import_backup(file_path: Path) -> list[dict]:
        """导入手机备份文件（SQLite DB）"""
        try:
            import sqlite3
            import re as _re

            def _safe_identifier(name: str) -> str:
                """白名单校验表名/列名，只允许字母数字下划线"""
                if not _re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
                    raise ValueError(f"非法标识符: {name}")
                return name

            conn = sqlite3.connect(str(file_path))
            cursor = conn.cursor()

            # 查找聊天记录表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            messages = []
            for table in tables:
                try:
                    safe_table = _safe_identifier(table)
                except ValueError:
                    continue

                cursor.execute(f"PRAGMA table_info({safe_table})")
                columns = [col[1].lower() for col in cursor.fetchall()]

                role_col = next((c for c in columns if c in ("role", "sender", "from_user", "is_sender")), None)
                text_col = next((c for c in columns if c in ("text", "content", "message", "msg")), None)
                time_col = next((c for c in columns if c in ("time", "timestamp", "create_time", "date")), None)

                if text_col:
                    # 校验列名白名单
                    safe_cols = []
                    for col_name in [text_col, role_col, time_col]:
                        if col_name:
                            try:
                                safe_cols.append(_safe_identifier(col_name))
                            except ValueError:
                                continue

                    cursor.execute(f"SELECT {', '.join(safe_cols)} FROM {safe_table}")
                    for row in cursor.fetchall():
                        msg = {"text": str(row[0]).strip()}
                        if role_col:
                            msg["role"] = ChatImporter._normalize_role(str(row[1]))
                        if time_col:
                            msg["time"] = str(row[-1])
                        if msg["text"]:
                            messages.append(msg)

            conn.close()
            return messages
        except Exception as e:
            console.print(f"[yellow]备份解析失败: {e}[/yellow]")
            return []

    @staticmethod
    def _normalize_role(raw: str) -> str:
        """统一角色名称"""
        raw = raw.strip().lower()
        # 精确匹配中文关键词（子串即可）
        me_chinese = ("我", "自己")
        if any(k in raw for k in me_chinese):
            return "me"
        # 英文关键词全词匹配，避免 "Lisa" 中的 "i" 被误判
        me_english = ("me", "self", "my")
        for kw in me_english:
            if re.search(r'\b' + re.escape(kw) + r'\b', raw):
                return "me"
        return "ex"
