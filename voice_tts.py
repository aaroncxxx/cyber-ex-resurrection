#!/usr/bin/env python3
"""
TTS 语音合成接口
"""

import asyncio
from pathlib import Path

from rich.console import Console

console = Console()


class TTSEngine:
    """TTS 语音合成引擎"""

    def __init__(self, config: dict, voice_dir: str, engine_name: str = "openvoice"):
        self.config = config
        self.voice_dir = Path(voice_dir)
        self.engine_name = engine_name
        self._engine = None

    def _get_engine(self):
        """延迟加载引擎"""
        if self._engine is None:
            from voice_clone import VoiceCloner
            cloner = VoiceCloner(self.config, self.engine_name)
            self._engine = cloner.engine

            # 加载已有的声音模型
            meta_file = self.voice_dir / "meta.json"
            if meta_file.exists():
                import json
                with open(meta_file) as f:
                    meta = json.load(f)
                if hasattr(self._engine, 'reference_audio'):
                    self._engine.reference_audio = Path(meta.get("reference_audio", ""))
                self._engine.model_dir = self.voice_dir

        return self._engine

    async def synthesize(self, text: str, output_path: Path = None) -> Path:
        """文字转语音"""
        engine = self._get_engine()

        if output_path is None:
            output_dir = self.voice_dir / "output"
            output_dir.mkdir(exist_ok=True)
            import hashlib
            hash_name = hashlib.md5(text.encode()).hexdigest()[:12]
            output_path = output_dir / f"{hash_name}.wav"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = await engine.synthesize(text, output_path)
            if result and result.exists() and result.stat().st_size > 0:
                return result
        except Exception as e:
            console.print(f"[yellow]语音合成失败: {e}[/yellow]")

        return output_path

    async def synthesize_batch(self, texts: list[str], output_dir: Path = None) -> list[Path]:
        """批量语音合成"""
        if output_dir is None:
            output_dir = self.voice_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for i, text in enumerate(texts):
            output_path = output_dir / f"batch_{i:04d}.wav"
            result = await self.synthesize(text, output_path)
            results.append(result)

        return results
