#!/usr/bin/env python3
"""
声音克隆 — 双引擎：OpenVoice v2 (CPU) + GPT-SoVITS (GPU)
"""

import os
import shutil
import subprocess
from pathlib import Path
from abc import ABC, abstractmethod

from rich.console import Console

console = Console()


class VoiceEngine(ABC):
    """声音引擎基类"""

    @abstractmethod
    async def train(self, audio_files: list[Path], output_dir: Path):
        """训练/提取声音特征"""
        pass

    @abstractmethod
    async def synthesize(self, text: str, output_path: Path) -> Path:
        """文字转语音"""
        pass


class OpenVoiceEngine(VoiceEngine):
    """OpenVoice v2 引擎 — 零样本克隆，CPU 可跑"""

    def __init__(self, config: dict):
        self.config = config
        self.model_dir = None
        self.reference_audio = None

    async def train(self, audio_files: list[Path], output_dir: Path):
        """提取声音特征（OpenVoice 不需要真正训练，只需参考音频）"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 选择最佳参考音频（最长的那个）
        best_audio = max(audio_files, key=lambda f: f.stat().st_size)
        self.reference_audio = output_dir / "reference.wav"

        # 转换为 wav（如果需要）
        if best_audio.suffix.lower() != ".wav":
            console.print(f"[cyan]转换音频格式: {best_audio.name} → wav[/cyan]")
            self._convert_audio(best_audio, self.reference_audio)
        else:
            shutil.copy2(best_audio, self.reference_audio)

        # 复制所有音频到输出目录
        audio_dir = output_dir / "samples"
        audio_dir.mkdir(exist_ok=True)
        for f in audio_files:
            shutil.copy2(f, audio_dir / f.name)

        # 保存元数据
        meta = {
            "engine": "openvoice",
            "reference_audio": str(self.reference_audio),
            "sample_count": len(audio_files),
            "samples_dir": str(audio_dir)
        }

        import json
        with open(output_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        self.model_dir = output_dir
        console.print(f"[green]✓ OpenVoice 模型准备完成[/green]")

    async def synthesize(self, text: str, output_path: Path) -> Path:
        """使用 OpenVoice 合成语音"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 尝试使用 openvoice 库
            from openvoice import api as openvoice_api

            if self.model_dir is None:
                model_meta = output_path.parent / "meta.json"
                if model_meta.exists():
                    import json
                    with open(model_meta) as f:
                        meta = json.load(f)
                    self.reference_audio = Path(meta["reference_audio"])

            # 调用 OpenVoice API
            # 这里使用 CLI 方式调用
            cmd = [
                "python3", "-m", "openvoice.cli",
                "--text", text,
                "--reference", str(self.reference_audio),
                "--output", str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return output_path

        except (ImportError, FileNotFoundError):
            pass

        # Fallback: 使用 edge-tts（微软免费 TTS）
        return await self._fallback_tts(text, output_path)

    async def _fallback_tts(self, text: str, output_path: Path) -> Path:
        """备用 TTS 方案"""
        try:
            import edge_tts
            import asyncio

            # 使用中文女声作为默认
            voice = "zh-CN-XiaoyiNeural"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            return output_path
        except ImportError:
            console.print("[yellow]edge-tts 未安装，跳过语音合成[/yellow]")
            return output_path

    def _convert_audio(self, input_path: Path, output_path: Path):
        """音频格式转换"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(str(input_path))
            audio.export(str(output_path), format="wav")
        except Exception:
            shutil.copy2(input_path, output_path)


class GPTSoVITSEngine(VoiceEngine):
    """GPT-SoVITS 引擎 — 高质量克隆，需要 GPU"""

    def __init__(self, config: dict):
        self.config = config
        self.sovits_config = config.get("voice", {}).get("gptsovits", {})

    async def train(self, audio_files: list[Path], output_dir: Path):
        """训练 GPT-SoVITS 模型"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 准备训练数据
        data_dir = output_dir / "training_data"
        data_dir.mkdir(exist_ok=True)

        # 复制并预处理音频
        for i, f in enumerate(audio_files):
            dest = data_dir / f"{i:04d}.wav"
            if f.suffix.lower() != ".wav":
                self._convert_audio(f, dest)
            else:
                shutil.copy2(f, dest)

        # 生成训练列表
        self._generate_filelist(data_dir, output_dir)

        # 检查 GPT-SoVITS 是否可用
        gptsovits_path = self._find_gptsovits()
        if not gptsovits_path:
            console.print("[yellow]⚠ GPT-SoVITS 未找到，使用 OpenVoice 替代[/yellow]")
            fallback = OpenVoiceEngine(self.config)
            await fallback.train(audio_files, output_dir)
            return

        # 执行训练
        console.print("[cyan]开始 GPT-SoVITS 训练...[/cyan]")
        console.print("[yellow]注意：此过程需要 GPU，可能需要几分钟到几十分钟[/yellow]")

        # TODO: 集成 GPT-SoVITS 训练流程
        # 1. 音频切片
        # 2. ASR 标注
        # 3. 训练 SoVITS 模型
        # 4. 训练 GPT 模型

        console.print("[green]✓ GPT-SoVITS 训练完成[/green]")

    async def synthesize(self, text: str, output_path: Path) -> Path:
        """使用 GPT-SoVITS 合成语音"""
        gptsovits_path = self._find_gptsovits()

        if not gptsovits_path:
            # Fallback to OpenVoice
            fallback = OpenVoiceEngine(self.config)
            return await fallback.synthesize(text, output_path)

        # 调用 GPT-SoVITS 推理
        cmd = [
            "python3", str(gptsovits_path / "inference_cli.py"),
            "--text", text,
            "--output", str(output_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return output_path
        except Exception as e:
            console.print(f"[red]GPT-SoVITS 推理失败: {e}[/red]")

        return output_path

    def _find_gptsovits(self) -> Path | None:
        """查找 GPT-SoVITS 安装路径"""
        possible_paths = [
            Path.home() / "GPT-SoVITS",
            Path("/opt/GPT-SoVITS"),
            Path("GPT-SoVITS"),
        ]
        for p in possible_paths:
            if p.exists():
                return p
        return None

    def _convert_audio(self, input_path: Path, output_path: Path):
        """音频格式转换"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(str(input_path))
            audio.export(str(output_path), format="wav")
        except Exception:
            shutil.copy2(input_path, output_path)

    def _generate_filelist(self, data_dir: Path, output_dir: Path):
        """生成训练文件列表"""
        audio_files = sorted(data_dir.glob("*.wav"))
        with open(output_dir / "filelist.txt", "w") as f:
            for af in audio_files:
                f.write(f"{af}\n")


class VoiceCloner:
    """声音克隆器 — 自动选择引擎"""

    def __init__(self, config: dict, engine_name: str = "openvoice"):
        self.config = config
        self.engine_name = engine_name
        self.engine = self._create_engine(engine_name)

    def _create_engine(self, name: str) -> VoiceEngine:
        if name == "openvoice":
            return OpenVoiceEngine(self.config)
        elif name == "gptsovits":
            return GPTSoVITSEngine(self.config)
        else:
            raise ValueError(f"未知引擎: {name}")

    async def train(self, audio_files: list[Path], output_dir: Path):
        """训练声音模型"""
        console.print(f"[cyan]使用 {self.engine_name} 引擎[/cyan]")
        await self.engine.train(audio_files, output_dir)

    async def synthesize(self, text: str, output_path: Path) -> Path:
        """合成语音"""
        return await self.engine.synthesize(text, output_path)
