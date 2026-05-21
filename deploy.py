#!/usr/bin/env python3
"""
一键部署 CLI — 无需 GUI，命令行全自动
用法:
    python3 deploy.py --input screenshots/ --voices voices/ --platform wechat
    python3 deploy.py --import chat.txt --voices voices/
    python3 deploy.py --input screenshots/ --clean-only
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.live import Live

console = Console()
BASE_DIR = Path(__file__).parent


def load_config():
    with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def check_ethics():
    consent_file = BASE_DIR / "data" / ".consent.json"
    if not consent_file.exists():
        console.print("[red]❌ 未通过伦理确认。请先运行: python3 main.py consent[/red]")
        sys.exit(1)


@dataclass
class DeployResult:
    stage: str
    success: bool
    data: dict = None
    error: str = None
    duration_ms: int = 0


@click.command()
@click.option("--input", "-i", "screenshot_dir", default=None, help="截图目录")
@click.option("--import-file", "-f", "import_path", default=None, help="导入聊天记录文件")
@click.option("--voices", "-v", "voice_dir", default=None, help="语音文件目录")
@click.option("--platform", "-p", default=None, type=click.Choice(["wechat", "qq", "feishu", "whatsapp"]))
@click.option("--ocr-engine", default="mimo_omni", type=click.Choice(["mimo_omni", "paddleocr", "easyocr"]))
@click.option("--voice-engine", "-e", default="openvoice", type=click.Choice(["openvoice", "gptsovits"]))
@click.option("--no-clean", is_flag=True, help="跳过数据清洗")
@click.option("--no-persona", is_flag=True, help="跳过人格建模")
@click.option("--no-voice", is_flag=True, help="跳过声音克隆")
@click.option("--clean-only", is_flag=True, help="仅清洗数据")
@click.option("--dry-run", is_flag=True, help="预览，不执行")
def deploy(screenshot_dir, import_path, voice_dir, platform, ocr_engine, voice_engine,
           no_clean, no_persona, no_voice, clean_only, dry_run):
    """🚀 一键部署 — 自动执行完整流程"""
    console.print(Panel.fit(
        "[bold magenta]🫀 复活吧我的赛博前任 — 一键部署[/bold magenta]\n"
        "[dim]v1.2.0[/dim]",
        border_style="magenta"
    ))

    check_ethics()
    config = load_config()
    results = []
    start_total = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:

        # 计算总步骤数
        steps = []
        if import_path:
            steps.append("import")
        elif screenshot_dir:
            steps.append("ocr")
        if not no_clean:
            steps.append("clean")
        if not no_persona:
            steps.append("persona")
        if voice_dir and not no_voice:
            steps.append("voice")
        if platform:
            steps.append("bot")
        if clean_only:
            steps = ["clean"]

        total = len(steps)
        task = progress.add_task("部署进度", total=total)

        chat_file = BASE_DIR / "data" / "chat_log.json"

        # Step 1: Import 或 OCR
        if "import" in steps:
            progress.update(task, description="📥 导入聊天记录...")
            start = time.time()
            try:
                from importers import ChatImporter
                path = Path(import_path)
                if path.is_dir():
                    messages = ChatImporter.import_directory(path)
                else:
                    messages = ChatImporter.import_file(path)
                chat_file.parent.mkdir(parents=True, exist_ok=True)
                with open(chat_file, "w", encoding="utf-8") as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)
                results.append(DeployResult("import", True, {"count": len(messages)},
                                            duration_ms=int((time.time() - start) * 1000)))
                console.print(f"  ✅ 导入 {len(messages)} 条消息")
            except Exception as e:
                results.append(DeployResult("import", False, error=str(e)))
                console.print(f"  ❌ 导入失败: {e}")
            progress.advance(task)

        elif "ocr" in steps:
            progress.update(task, description="📸 截图 OCR...")
            start = time.time()
            try:
                from ocr_engines import MultiEngineOCR
                ocr = MultiEngineOCR(config, [ocr_engine])
                sp = Path(screenshot_dir)
                exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
                screenshots = sorted([f for f in sp.iterdir() if f.suffix.lower() in exts])
                messages = []
                for img in screenshots:
                    try:
                        results_list = ocr.recognize(img)
                        messages.extend(results_list)
                    except Exception as e:
                        console.print(f"  ⚠️ {img.name}: {e}")
                chat_file.parent.mkdir(parents=True, exist_ok=True)
                with open(chat_file, "w", encoding="utf-8") as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)
                results.append(DeployResult("ocr", True, {"count": len(messages)},
                                            duration_ms=int((time.time() - start) * 1000)))
                console.print(f"  ✅ OCR {len(messages)} 条消息")
            except Exception as e:
                results.append(DeployResult("ocr", False, error=str(e)))
                console.print(f"  ❌ OCR 失败: {e}")
            progress.advance(task)

        # Step 2: Clean
        if "clean" in steps:
            progress.update(task, description="🧹 数据清洗...")
            start = time.time()
            try:
                from data_cleaner import clean_chat_file
                cleaned_file = BASE_DIR / "data" / "chat_log_cleaned.json"
                if chat_file.exists():
                    clean_chat_file(chat_file, cleaned_file, config)
                    chat_file = cleaned_file
                results.append(DeployResult("clean", True, duration_ms=int((time.time() - start) * 1000)))
                console.print("  ✅ 清洗完成")
            except Exception as e:
                results.append(DeployResult("clean", False, error=str(e)))
                console.print(f"  ❌ 清洗失败: {e}")
            progress.advance(task)

        if clean_only:
            progress.update(task, description="✅ 完成")
            _print_summary(results, time.time() - start_total)
            return

        # Step 3: Persona
        if "persona" in steps:
            progress.update(task, description="🧠 人格建模...")
            start = time.time()
            try:
                from persona_builder import PersonaBuilder
                builder = PersonaBuilder(config)
                # 优先使用清洗后的文件
                persona_input = BASE_DIR / "data" / "chat_log_cleaned.json"
                if not persona_input.exists():
                    persona_input = chat_file
                if persona_input.exists():
                    persona_text = asyncio.run(builder.build(persona_input))
                    persona_path = BASE_DIR / "data" / "persona.md"
                    with open(persona_path, "w", encoding="utf-8") as f:
                        f.write(persona_text)
                    results.append(DeployResult("persona", True, {"length": len(persona_text)},
                                                duration_ms=int((time.time() - start) * 1000)))
                    console.print(f"  ✅ 人格生成 ({len(persona_text)} 字符)")
            except Exception as e:
                results.append(DeployResult("persona", False, error=str(e)))
                console.print(f"  ❌ 人格失败: {e}")
            progress.advance(task)

        # Step 4: Voice
        if "voice" in steps:
            progress.update(task, description="🎤 声音克隆...")
            start = time.time()
            try:
                from voice_clone import VoiceCloner
                cloner = VoiceCloner(config, voice_engine)
                vp = Path(voice_dir)
                exts = {".wav", ".mp3", ".ogg", ".m4a", ".amr", ".silk", ".flac"}
                audio_files = sorted([f for f in vp.iterdir() if f.suffix.lower() in exts])
                output_dir = BASE_DIR / "data" / "voice_model"
                asyncio.run(cloner.train(audio_files, output_dir))
                results.append(DeployResult("voice", True, {"engine": voice_engine, "samples": len(audio_files)},
                                            duration_ms=int((time.time() - start) * 1000)))
                console.print(f"  ✅ 声音训练完成 ({voice_engine})")
            except Exception as e:
                results.append(DeployResult("voice", False, error=str(e)))
                console.print(f"  ❌ 声音失败: {e}")
            progress.advance(task)

        # Step 5: Bot
        if "bot" in steps:
            progress.update(task, description=f"📱 启动 {platform} 机器人...")
            start = time.time()
            try:
                from bots import get_bot
                BotClass = get_bot(platform)
                bot_config = config.get("bots", {}).get(platform, {})
                bot = BotClass(config, bot_config, str(BASE_DIR / "data" / "persona.md"),
                              str(BASE_DIR / "data" / "voice_model"), voice_engine)
                results.append(DeployResult("bot", True, {"platform": platform},
                                            duration_ms=int((time.time() - start) * 1000)))
                console.print(f"  ✅ {platform} 机器人就绪")
            except Exception as e:
                results.append(DeployResult("bot", False, error=str(e)))
                console.print(f"  ❌ 机器人失败: {e}")
            progress.advance(task)

        progress.update(task, description="✅ 部署完成")

    _print_summary(results, time.time() - start_total)


def _print_summary(results, total_time):
    """打印部署摘要"""
    table = Table(title="📋 部署摘要", border_style="cyan")
    table.add_column("阶段", style="cyan")
    table.add_column("状态", justify="center")
    table.add_column("耗时", justify="right")
    table.add_column("详情", style="dim")

    success_count = 0
    for r in results:
        status = "✅" if r.success else "❌"
        if r.success:
            success_count += 1
        duration = f"{r.duration_ms}ms" if r.duration_ms else "—"
        detail = json.dumps(r.data, ensure_ascii=False) if r.data else (r.error or "—")
        table.add_row(r.stage, status, duration, detail[:60])

    console.print(table)
    console.print(f"\n⏱️  总耗时: {total_time:.1f}s | ✅ {success_count}/{len(results)} 成功")


if __name__ == "__main__":
    deploy()
