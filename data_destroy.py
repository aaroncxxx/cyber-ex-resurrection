#!/usr/bin/env python3
"""
一键数据销毁 — 安全删除所有本地数据
"""

import json
import os
import shutil
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

console = Console()

# 可销毁的数据目录
DESTROY_TARGETS = [
    ("data/screenshots/", "聊天截图原件"),
    ("data/chat_log.json", "提取的聊天记录"),
    ("data/chat_log_cleaned.json", "清洗后的聊天记录"),
    ("data/persona.md", "人格模型文件"),
    ("data/voice_model/", "声音克隆模型"),
    ("data/memory/", "对话记忆数据"),
    ("data/memory.json", "记忆索引"),
    ("data/imported/", "导入的原始文件"),
    ("data/logs/", "运行日志"),
    ("data/.consent.json", "伦理同意记录"),
]


class DataDestroyer:
    """数据销毁器"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def scan(self) -> list[dict]:
        """扫描所有可销毁的数据"""
        results = []
        for rel_path, description in DESTROY_TARGETS:
            full_path = self.base_dir / rel_path
            exists = full_path.exists()
            size = 0
            file_count = 0

            if exists:
                if full_path.is_file():
                    size = full_path.stat().st_size
                    file_count = 1
                elif full_path.is_dir():
                    for f in full_path.rglob("*"):
                        if f.is_file():
                            size += f.stat().st_size
                            file_count += 1

            results.append({
                "path": rel_path,
                "description": description,
                "exists": exists,
                "size": size,
                "file_count": file_count,
            })
        return results

    def show_status(self):
        """展示数据状态"""
        results = self.scan()

        table = Table(title="📊 本地数据扫描", border_style="cyan")
        table.add_column("路径", style="dim")
        table.add_column("说明", style="cyan")
        table.add_column("状态", justify="center")
        table.add_column("文件数", justify="right")
        table.add_column("大小", justify="right")

        total_size = 0
        total_files = 0
        for r in results:
            status = "[green]✓ 存在[/green]" if r["exists"] else "[dim]— 无[/dim]"
            size_str = self._format_size(r["size"]) if r["exists"] else "—"
            count_str = str(r["file_count"]) if r["exists"] else "—"
            table.add_row(r["path"], r["description"], status, count_str, size_str)
            if r["exists"]:
                total_size += r["size"]
                total_files += r["file_count"]

        console.print(table)
        console.print(f"\n[bold]总计: {total_files} 个文件, {self._format_size(total_size)}[/bold]")

    def destroy_all(self, confirm: bool = True) -> dict:
        """销毁所有数据"""
        if confirm:
            console.print(Panel(
                "[bold red]⚠️ 即将永久删除以下所有数据：[/bold red]\n\n"
                "• 聊天截图原件\n"
                "• 提取和清洗后的聊天记录\n"
                "• 人格模型文件\n"
                "• 声音克隆模型\n"
                "• 对话记忆数据\n"
                "• 运行日志\n"
                "• 伦理同意记录\n\n"
                "[bold red]此操作不可撤销！[/bold red]",
                title="🔥 数据销毁确认",
                border_style="red"
            ))

            if not Confirm.ask("确认销毁所有数据？", default=False):
                console.print("[yellow]已取消。[/yellow]")
                return {"cancelled": True}

        destroyed = []
        errors = []

        for rel_path, description in DESTROY_TARGETS:
            full_path = self.base_dir / rel_path
            if not full_path.exists():
                continue

            try:
                if full_path.is_file():
                    # 安全覆写后删除
                    self._secure_delete_file(full_path)
                elif full_path.is_dir():
                    # 安全删除目录下所有文件
                    for f in full_path.rglob("*"):
                        if f.is_file():
                            self._secure_delete_file(f)
                    shutil.rmtree(full_path)

                destroyed.append({"path": rel_path, "description": description})
                console.print(f"  [green]✓[/green] 已销毁: {rel_path}")
            except Exception as e:
                errors.append({"path": rel_path, "error": str(e)})
                console.print(f"  [red]✗[/red] 失败: {rel_path} — {e}")

        # 删除日志
        console.print(Panel(
            f"[green]✅ 已销毁 {len(destroyed)} 项数据[/green]"
            + (f"\n[red]❌ {len(errors)} 项失败[/red]" if errors else ""),
            title="销毁完成",
            border_style="green" if not errors else "red"
        ))

        return {"destroyed": destroyed, "errors": errors}

    def destroy_selective(self, targets: list[str], confirm: bool = True) -> dict:
        """选择性销毁"""
        if confirm:
            console.print("[yellow]即将销毁:[/yellow]")
            for t in targets:
                console.print(f"  • {t}")
            if not Confirm.ask("确认？", default=False):
                return {"cancelled": True}

        destroyed = []
        for rel_path in targets:
            full_path = self.base_dir / rel_path
            if not full_path.exists():
                continue
            try:
                if full_path.is_file():
                    self._secure_delete_file(full_path)
                elif full_path.is_dir():
                    for f in full_path.rglob("*"):
                        if f.is_file():
                            self._secure_delete_file(f)
                    shutil.rmtree(full_path)
                destroyed.append(rel_path)
            except Exception as e:
                console.print(f"[red]删除失败 {rel_path}: {e}[/red]")

        return {"destroyed": destroyed}

    def _secure_delete_file(self, filepath: Path):
        """安全删除文件 — 覆写后删除"""
        size = filepath.stat().st_size
        with open(filepath, "wb") as f:
            f.write(b"\x00" * size)
            f.flush()
            os.fsync(f.fileno())
        filepath.unlink()

    def _format_size(self, size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
