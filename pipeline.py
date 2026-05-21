#!/usr/bin/env python3
"""
Pipeline — 截图→人格→声音→IM 统一管线
可复用于：客服质检回放、历史人物对话、虚拟主播等场景
"""

import asyncio
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

console = Console()


@dataclass
class PipelineConfig:
    """管线配置"""
    # OCR
    ocr_enabled: bool = True
    ocr_prompt: str = None

    # 人格
    persona_enabled: bool = True
    persona_output: str = "data/persona.md"

    # 声音
    voice_enabled: bool = True
    voice_engine: str = "openvoice"
    voice_output: str = "data/voice_model/"

    # 记忆
    memory_enabled: bool = True
    memory_dir: str = "data/memory"

    # 机器人
    bot_platform: str = None  # wechat/qq/feishu/whatsapp
    bot_persona: str = None
    bot_voice_dir: str = None

    # 输出
    output_dir: str = "data/"


@dataclass
class PipelineResult:
    """管线执行结果"""
    stage: str
    success: bool
    data: dict = field(default_factory=dict)
    error: str = None
    duration_ms: int = 0


class Pipeline:
    """
    统一管线 — 截图→人格→声音→IM

    用法:
        pipe = Pipeline(config)
        results = await pipe.run_full(screenshots, audio_files)

    可单独调用每个阶段:
        result = await pipe.stage_ocr(screenshots)
        result = await pipe.stage_persona(chat_file)
        result = await pipe.stage_voice(audio_files)
        result = await pipe.stage_bot(platform)
    """

    def __init__(self, config: dict, pipeline_config: PipelineConfig = None):
        self.config = config
        self.pc = pipeline_config or PipelineConfig()

    async def run_full(self, screenshots: list[Path] = None,
                       audio_files: list[Path] = None) -> list[PipelineResult]:
        """运行完整管线"""
        results = []

        # Stage 1: OCR
        if screenshots and self.pc.ocr_enabled:
            console.print(Panel("📸 Stage 1: 截图 OCR 提取", style="cyan"))
            r = await self.stage_ocr(screenshots)
            results.append(r)
            if not r.success:
                console.print(f"[red]OCR 失败: {r.error}[/red]")
                return results
            chat_file = Path(r.data["output"])
        else:
            chat_file = Path(self.pc.output_dir) / "chat_log.json"

        # Stage 2: Persona
        if self.pc.persona_enabled and chat_file.exists():
            console.print(Panel("🧠 Stage 2: 人格建模", style="magenta"))
            r = await self.stage_persona(chat_file)
            results.append(r)
            if not r.success:
                console.print(f"[yellow]人格建模失败: {r.error}[/yellow]")

        # Stage 3: Voice
        if audio_files and self.pc.voice_enabled:
            console.print(Panel("🎤 Stage 3: 声音克隆", style="green"))
            r = await self.stage_voice(audio_files)
            results.append(r)
            if not r.success:
                console.print(f"[yellow]声音克隆失败: {r.error}[/yellow]")

        # Stage 4: Bot (可选)
        if self.pc.bot_platform:
            console.print(Panel(f"📱 Stage 4: 启动 {self.pc.bot_platform} 机器人", style="yellow"))
            r = await self.stage_bot(self.pc.bot_platform)
            results.append(r)

        return results

    async def stage_ocr(self, screenshots: list[Path]) -> PipelineResult:
        """Stage 1: OCR 提取"""
        import time
        start = time.time()

        try:
            from ocr_extract import OCRExtractor
            extractor = OCRExtractor(self.config)
            messages = await extractor.extract_all(screenshots, self.pc.ocr_prompt)

            output_path = Path(self.pc.output_dir) / "chat_log.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)

            return PipelineResult(
                stage="ocr",
                success=True,
                data={"output": str(output_path), "message_count": len(messages)},
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return PipelineResult(stage="ocr", success=False, error=str(e))

    async def stage_persona(self, chat_file: Path) -> PipelineResult:
        """Stage 2: 人格建模"""
        import time
        start = time.time()

        try:
            from persona_builder import PersonaBuilder
            builder = PersonaBuilder(self.config)
            persona_text = await builder.build(chat_file)

            output_path = Path(self.pc.persona_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(persona_text)

            return PipelineResult(
                stage="persona",
                success=True,
                data={"output": str(output_path), "length": len(persona_text)},
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return PipelineResult(stage="persona", success=False, error=str(e))

    async def stage_voice(self, audio_files: list[Path]) -> PipelineResult:
        """Stage 3: 声音克隆"""
        import time
        start = time.time()

        try:
            from voice_clone import VoiceCloner
            cloner = VoiceCloner(self.config, self.pc.voice_engine)
            output_dir = Path(self.pc.voice_output)
            await cloner.train(audio_files, output_dir)

            return PipelineResult(
                stage="voice",
                success=True,
                data={"output": str(output_dir), "engine": self.pc.voice_engine, "samples": len(audio_files)},
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return PipelineResult(stage="voice", success=False, error=str(e))

    async def stage_bot(self, platform: str) -> PipelineResult:
        """Stage 4: 启动 IM 机器人"""
        import time
        start = time.time()

        try:
            from bots import get_bot
            BotClass = get_bot(platform)

            bot_config = self.config.get("bots", {}).get(platform, {})
            persona_file = self.pc.bot_persona or self.pc.persona_output
            voice_dir = self.pc.bot_voice_dir or self.pc.voice_output

            bot_instance = BotClass(
                self.config, bot_config,
                persona_file, voice_dir, self.pc.voice_engine
            )

            return PipelineResult(
                stage="bot",
                success=True,
                data={"platform": platform, "class": BotClass.__name__},
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return PipelineResult(stage="bot", success=False, error=str(e))

    def summary(self, results: list[PipelineResult]) -> str:
        """生成管线执行摘要"""
        lines = ["📋 Pipeline 执行摘要", "━" * 40]
        total_ms = 0
        for r in results:
            status = "✅" if r.success else "❌"
            lines.append(f"{status} {r.stage}: {r.duration_ms}ms")
            if r.data:
                for k, v in r.data.items():
                    lines.append(f"   {k}: {v}")
            if r.error:
                lines.append(f"   ❌ {r.error}")
            total_ms += r.duration_ms
        lines.append(f"\n⏱️  总耗时: {total_ms}ms")
        return "\n".join(lines)
