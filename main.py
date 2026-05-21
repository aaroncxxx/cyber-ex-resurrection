#!/usr/bin/env python3
"""
复活吧我的赛博前任 — 主入口
Cyber Ex Resurrection — Main Entry Point

v1.1.1: 伦理声明 | 一键销毁 | 多引擎OCR | 智能清洗 | 多格式导入
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def banner():
    console.print(Panel.fit(
        "[bold magenta]🫀 复活吧我的赛博前任[/bold magenta]\n"
        "[dim]Cyber Ex Resurrection v1.1.1[/dim]",
        border_style="magenta"
    ))


def check_ethics():
    """检查伦理确认状态"""
    from ethics import EthicsChecker
    checker = EthicsChecker(BASE_DIR)
    if not checker.ensure_consent():
        console.print("[red]未通过伦理确认，无法继续。[/red]")
        sys.exit(1)


@click.group()
def cli():
    """🫀 复活吧我的赛博前任"""
    pass


# ─────────────────────────────────────────────
# Consent: 伦理声明
# ─────────────────────────────────────────────
@cli.command()
@click.option("--show-legal", is_flag=True, help="显示法律条文参考")
@click.option("--revoke", is_flag=True, help="撤销已有的同意记录")
def consent(show_legal, revoke):
    """查看/确认伦理声明"""
    from ethics import EthicsChecker
    checker = EthicsChecker(BASE_DIR)

    if show_legal:
        checker.show_legal_references()
        return

    if revoke:
        checker.revoke_consent()
        return

    if checker.check_consent():
        console.print("[green]✅ 已通过伦理确认。[/green]")
        if click.confirm("是否重新确认？"):
            checker.revoke_consent()
            checker.require_consent()
    else:
        checker.require_consent()


# ─────────────────────────────────────────────
# Destroy: 一键数据销毁
# ─────────────────────────────────────────────
@cli.command()
@click.option("--scan", is_flag=True, help="仅扫描，不销毁")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
@click.option("--target", "-t", multiple=True, help="指定销毁目标路径")
def destroy(scan, yes, target):
    """🔥 一键数据销毁"""
    banner()
    from data_destroy import DataDestroyer

    destroyer = DataDestroyer(BASE_DIR)

    if scan:
        destroyer.show_status()
        return

    if target:
        results = destroyer.destroy_selective(list(target), confirm=not yes)
    else:
        results = destroyer.destroy_all(confirm=not yes)


# ─────────────────────────────────────────────
# OCR: 截图提取对话（多引擎）
# ─────────────────────────────────────────────
@cli.command()
@click.option("--input", "-i", "input_dir", required=True, help="截图目录")
@click.option("--output", "-o", "output_file", default="data/chat_log.json", help="输出文件")
@click.option("--engine", "-e", default="mimo_omni",
              type=click.Choice(["mimo_omni", "paddleocr", "easyocr", "multi"]),
              help="OCR 引擎")
@click.option("--prompt", "-p", default=None, help="自定义 OCR 提示词")
def ocr(input_dir, output_file, engine, prompt):
    """从聊天截图提取对话（多引擎）"""
    banner()
    check_ethics()

    input_path = Path(input_dir)
    if not input_path.exists():
        console.print(f"[red]目录不存在: {input_path}[/red]")
        return

    screenshots = sorted([
        f for f in input_path.iterdir()
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    ])

    if not screenshots:
        console.print("[red]未找到图片文件[/red]")
        return

    console.print(f"[green]找到 {len(screenshots)} 张截图[/green]")

    if engine == "multi":
        from ocr_engines import MultiEngineOCR
        multi = MultiEngineOCR(load_config(), ["paddleocr", "easyocr", "mimo_omni"])
        all_messages = []
        for img in screenshots:
            try:
                results = multi.recognize(img)
                all_messages.extend(results)
            except Exception as e:
                console.print(f"[red]{img.name}: {e}[/red]")
        messages = all_messages
    else:
        from ocr_engines import MultiEngineOCR
        ocr_engine = MultiEngineOCR(load_config(), [engine])
        messages = []
        for img in screenshots:
            try:
                results = ocr_engine.recognize(img)
                messages.extend(results)
            except Exception as e:
                console.print(f"[red]{img.name}: {e}[/red]")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    console.print(f"[green]✅ 提取 {len(messages)} 条消息 → {output_path}[/green]")


# ─────────────────────────────────────────────
# Import: 多格式导入
# ─────────────────────────────────────────────
@cli.command()
@click.option("--input", "-i", "input_path", required=True, help="文件或目录路径")
@click.option("--output", "-o", "output_file", default="data/chat_log.json", help="输出文件")
@click.option("--format", "-f", "fmt", default=None,
              type=click.Choice(["json", "csv", "html", "wechat_export", "txt_timestamped", "txt_plain", "backup"]),
              help="指定格式（默认自动检测）")
def import_chat(input_path, output_file, fmt):
    """导入聊天记录（支持 txt/csv/html/备份）"""
    banner()
    check_ethics()

    from importers import ChatImporter

    path = Path(input_path)
    if path.is_dir():
        messages = ChatImporter.import_directory(path)
    elif path.is_file():
        messages = ChatImporter.import_file(path, format=fmt)
    else:
        console.print(f"[red]路径不存在: {path}[/red]")
        return

    if not messages:
        console.print("[yellow]未导入任何消息[/yellow]")
        return

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    console.print(f"[green]✅ 导入 {len(messages)} 条消息 → {output_path}[/green]")


# ─────────────────────────────────────────────
# Clean: 智能数据清洗
# ─────────────────────────────────────────────
@cli.command()
@click.option("--input", "-i", "input_file", default="data/chat_log.json", help="输入聊天记录")
@click.option("--output", "-o", "output_file", default="data/chat_log_cleaned.json", help="输出文件")
@click.option("--no-system", is_flag=True, help="不过滤系统消息")
@click.option("--no-ads", is_flag=True, help="不过滤广告")
@click.option("--no-dedup", is_flag=True, help="不去重")
@click.option("--keep-emoji-only", is_flag=True, help="保留纯表情消息")
def clean(input_file, output_file, no_system, no_ads, no_dedup, keep_emoji_only):
    """智能数据清洗"""
    banner()

    from data_cleaner import clean_chat_file

    options = {
        "remove_system": not no_system,
        "remove_ads": not no_ads,
        "remove_duplicates": not no_dedup,
        "remove_invalid": not keep_emoji_only,
    }

    clean_chat_file(Path(input_file), Path(output_file), load_config(), options)


# ─────────────────────────────────────────────
# Persona: 构建人格
# ─────────────────────────────────────────────
@cli.command()
@click.option("--chat", "-c", "chat_file", default="data/chat_log_cleaned.json", help="聊天记录 JSON")
@click.option("--output", "-o", "output_file", default="data/persona.md", help="输出人格文件")
def persona(chat_file, output_file):
    """从聊天记录构建人格模型"""
    banner()
    check_ethics()

    from persona_builder import PersonaBuilder

    builder = PersonaBuilder(load_config())
    persona_text = asyncio.run(builder.build(Path(chat_file)))

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(persona_text)

    console.print(f"[green]✅ 人格模型已生成 → {output_path}[/green]")
    console.print(Panel(persona_text[:500] + "...", title="人格预览", border_style="cyan"))


# ─────────────────────────────────────────────
# Voice: 声音克隆
# ─────────────────────────────────────────────
@cli.command()
@click.option("--input", "-i", "input_dir", required=True, help="语音文件目录")
@click.option("--output", "-o", "output_dir", default="data/voice_model/", help="输出目录")
@click.option("--engine", "-e", default=None, type=click.Choice(["openvoice", "gptsovits"]), help="克隆引擎")
def voice(input_dir, output_dir, engine):
    """声音克隆训练"""
    banner()
    check_ethics()

    from voice_clone import VoiceCloner

    config = load_config()
    engine = engine or config.get("engine", "openvoice")

    input_path = Path(input_dir)
    if not input_path.exists():
        console.print(f"[red]目录不存在: {input_path}[/red]")
        return

    audio_files = sorted([
        f for f in input_path.iterdir()
        if f.suffix.lower() in (".wav", ".mp3", ".ogg", ".silk", ".amr", ".m4a", ".flac")
    ])

    if not audio_files:
        console.print("[red]未找到音频文件[/red]")
        return

    console.print(f"[green]找到 {len(audio_files)} 个音频文件[/green]")
    console.print(f"[cyan]引擎: {engine}[/cyan]")

    cloner = VoiceCloner(config, engine)
    asyncio.run(cloner.train(audio_files, Path(output_dir)))

    console.print(f"[green]✅ 声音模型已保存 → {output_dir}[/green]")


# ─────────────────────────────────────────────
# Chat: CLI 交互聊天
# ─────────────────────────────────────────────
@cli.command()
@click.option("--persona", "-p", "persona_file", default="data/persona.md", help="人格文件")
@click.option("--voice", "-v", "voice_dir", default="data/voice_model/", help="声音模型目录")
@click.option("--engine", "-e", default=None, type=click.Choice(["openvoice", "gptsovits"]))
@click.option("--no-voice", is_flag=True, help="禁用语音")
def chat(persona_file, voice_dir, engine, no_voice):
    """CLI 交互聊天"""
    banner()
    check_ethics()

    from chat_engine import ChatEngine

    config = load_config()
    engine = engine or config.get("engine", "openvoice")

    engine_obj = ChatEngine(config, persona_file, voice_dir, engine, enable_voice=not no_voice)

    console.print("[dim]输入消息开始聊天，输入 'quit' 退出[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]你: [/bold green]")
            if user_input.strip().lower() in ("quit", "exit", "q"):
                console.print("[dim]再见...[/dim]")
                break
            if not user_input.strip():
                continue

            response = asyncio.run(engine_obj.chat(user_input))
            console.print(f"[bold magenta]TA: [/bold magenta]{response['text']}")

            if response.get("voice_path") and not no_voice:
                console.print(f"[dim]🎤 语音已生成: {response['voice_path']}[/dim]")

        except KeyboardInterrupt:
            console.print("\n[dim]再见...[/dim]")
            break


# ─────────────────────────────────────────────
# Bot: 启动 IM 机器人
# ─────────────────────────────────────────────
@cli.command()
@click.option("--platform", "-p", required=True, type=click.Choice(["wechat", "qq", "feishu", "whatsapp"]))
@click.option("--persona", "persona_file", default="data/persona.md", help="人格文件")
@click.option("--voice", "voice_dir", default="data/voice_model/", help="声音模型目录")
@click.option("--engine", "-e", default=None)
def bot(platform, persona_file, voice_dir, engine):
    """启动 IM 机器人"""
    banner()
    check_ethics()

    config = load_config()
    engine = engine or config.get("engine", "openvoice")

    bot_config = config["bots"].get(platform, {})
    if not bot_config.get("enabled"):
        console.print(f"[red]{platform} 机器人未启用，请在 config.json 中配置[/red]")
        return

    console.print(f"[cyan]启动 {platform} 机器人...[/cyan]")

    from bots import get_bot
    BotClass = get_bot(platform)
    bot_instance = BotClass(config, bot_config, persona_file, voice_dir, engine)
    asyncio.run(bot_instance.start())


# ─────────────────────────────────────────────
# Pipeline: 完整管线
# ─────────────────────────────────────────────
@cli.command()
@click.option("--screenshots", "-s", "screenshot_dir", default=None, help="截图目录")
@click.option("--voices", "-v", "voice_dir", default=None, help="语音文件目录")
@click.option("--import-file", "-f", "import_path", default=None, help="导入聊天记录文件")
@click.option("--platform", "-p", default=None, type=click.Choice(["wechat", "qq", "feishu", "whatsapp"]))
@click.option("--engine", "-e", default=None, type=click.Choice(["openvoice", "gptsovits"]))
@click.option("--ocr-engine", default="mimo_omni", type=click.Choice(["mimo_omni", "paddleocr", "easyocr", "multi"]))
@click.option("--no-voice", is_flag=True, help="跳过声音克隆")
@click.option("--no-ocr", is_flag=True, help="跳过 OCR")
@click.option("--no-clean", is_flag=True, help="跳过数据清洗")
def pipeline(screenshot_dir, voice_dir, import_path, platform, engine, ocr_engine, no_voice, no_ocr, no_clean):
    """完整管线：截图/导入→清洗→人格→声音→IM"""
    banner()
    check_ethics()

    config = load_config()
    engine = engine or config.get("engine", "openvoice")

    # Stage 0: 导入或 OCR
    if import_path:
        console.print(Panel("📥 Stage 0: 导入聊天记录", style="cyan"))
        from importers import ChatImporter
        p = Path(import_path)
        if p.is_dir():
            messages = ChatImporter.import_directory(p)
        else:
            messages = ChatImporter.import_file(p)

        chat_log_path = Path("data/chat_log.json")
        chat_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(chat_log_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)

    elif screenshot_dir and not no_ocr:
        console.print(Panel("📸 Stage 1: 截图 OCR 提取", style="cyan"))
        from ocr_engines import MultiEngineOCR
        sp = Path(screenshot_dir)
        screenshots = sorted([
            f for f in sp.iterdir()
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp")
        ])
        ocr = MultiEngineOCR(config, [ocr_engine] if ocr_engine != "multi" else ["paddleocr", "easyocr", "mimo_omni"])
        messages = []
        for img in screenshots:
            try:
                results = ocr.recognize(img)
                messages.extend(results)
            except Exception as e:
                console.print(f"[red]{img.name}: {e}[/red]")

        chat_log_path = Path("data/chat_log.json")
        chat_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(chat_log_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    else:
        chat_log_path = Path("data/chat_log.json")

    # Stage 1.5: 清洗
    if not no_clean and chat_log_path.exists():
        console.print(Panel("🧹 Stage 1.5: 智能数据清洗", style="cyan"))
        from data_cleaner import clean_chat_file
        cleaned_path = Path("data/chat_log_cleaned.json")
        clean_chat_file(chat_log_path, cleaned_path, config)
        chat_log_path = cleaned_path

    # Stage 2: 人格建模
    if chat_log_path.exists():
        console.print(Panel("🧠 Stage 2: 人格建模", style="magenta"))
        from persona_builder import PersonaBuilder
        builder = PersonaBuilder(config)
        persona_text = asyncio.run(builder.build(chat_log_path))
        persona_path = Path("data/persona.md")
        persona_path.parent.mkdir(parents=True, exist_ok=True)
        with open(persona_path, "w", encoding="utf-8") as f:
            f.write(persona_text)

    # Stage 3: 声音克隆
    audio_files = None
    if voice_dir and not no_voice:
        vp = Path(voice_dir)
        if vp.exists():
            audio_files = sorted([
                f for f in vp.iterdir()
                if f.suffix.lower() in (".wav", ".mp3", ".ogg", ".silk", ".amr", ".m4a", ".flac")
            ])
            console.print(Panel("🎤 Stage 3: 声音克隆", style="green"))
            from voice_clone import VoiceCloner
            cloner = VoiceCloner(config, engine)
            asyncio.run(cloner.train(audio_files, Path("data/voice_model/")))

    # Stage 4: Bot
    if platform:
        console.print(Panel(f"📱 Stage 4: 启动 {platform} 机器人", style="yellow"))
        from bots import get_bot
        BotClass = get_bot(platform)
        bot_config = config.get("bots", {}).get(platform, {})
        bot_instance = BotClass(config, bot_config, "data/persona.md", "data/voice_model/", engine)
        asyncio.run(bot_instance.start())

    console.print("[green]✅ Pipeline 完成[/green]")


# ─────────────────────────────────────────────
# Info: 查看状态
# ─────────────────────────────────────────────
@cli.command()
def info():
    """查看配置和状态"""
    banner()
    config = load_config()

    table = Table(title="配置概览")
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")

    table.add_row("版本", "v1.1.1")
    table.add_row("声音引擎", config.get("engine", "openvoice"))
    table.add_row("人格文件", config["persona"]["data_path"])

    # 伦理状态
    from ethics import EthicsChecker
    checker = EthicsChecker(BASE_DIR)
    ethics_status = "✅ 已确认" if checker.check_consent() else "❌ 未确认"
    table.add_row("伦理确认", ethics_status)

    for name, bot_conf in config["bots"].items():
        status = "✅ 启用" if bot_conf.get("enabled") else "❌ 禁用"
        table.add_row(f"机器人: {name}", status)

    console.print(table)


if __name__ == "__main__":
    cli()
