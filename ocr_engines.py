#!/usr/bin/env python3
"""
多引擎 OCR — PaddleOCR / EasyOCR / MIMO Omni
支持表情包、手写体、特殊符号识别
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class OCREngine:
    """OCR 引擎基类"""
    name: str = "base"

    def recognize(self, image_path: Path) -> list[dict]:
        raise NotImplementedError


class PaddleOCREngine(OCREngine):
    """PaddleOCR 引擎 — 支持手写体、特殊符号、竖排文字"""
    name = "paddleocr"

    def __init__(self, lang: str = "ch"):
        self.lang = lang
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    show_log=False,
                    use_gpu=False,
                )
            except ImportError:
                raise ImportError("PaddleOCR 未安装: pip install paddleocr")
        return self._ocr

    def recognize(self, image_path: Path) -> list[dict]:
        """识别图片，返回 [{text, confidence, bbox}]"""
        ocr = self._get_ocr()
        result = ocr.ocr(str(image_path), cls=True)

        items = []
        if result and result[0]:
            for line in result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = line[1][1]
                items.append({
                    "text": text,
                    "confidence": confidence,
                    "bbox": bbox,
                    "engine": self.name,
                })
        return items


class EasyOCREngine(OCREngine):
    """EasyOCR 引擎 — 多语言支持好，对表情包和特殊字符友好"""
    name = "easyocr"

    def __init__(self, langs: list[str] = None):
        self.langs = langs or ["ch_sim", "en"]
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self.langs, gpu=False)
            except ImportError:
                raise ImportError("EasyOCR 未安装: pip install easyocr")
        return self._reader

    def recognize(self, image_path: Path) -> list[dict]:
        """识别图片，返回 [{text, confidence, bbox}]"""
        reader = self._get_reader()
        results = reader.readtext(str(image_path))

        items = []
        for bbox, text, confidence in results:
            items.append({
                "text": text,
                "confidence": confidence,
                "bbox": [list(map(list, bbox))],
                "engine": self.name,
            })
        return items


class MIMOOmniEngine(OCREngine):
    """MIMO Omni 多模态引擎 — 语义理解最强，适合复杂聊天截图"""
    name = "mimo_omni"

    DEFAULT_PROMPT = """请识别这张聊天截图中的所有对话内容。

要求：
1. 识别每条消息的发送者（区分"我"和"对方"）
2. 提取消息文本内容
3. 如果有时间戳，提取时间
4. 如果有表情包/图片/语音消息，标注为 [表情]、[图片]、[语音]
5. 如果有撤回消息，标注为 [撤回了一条消息]
6. 按时间顺序排列

输出 JSON 数组格式：
[
  {"role": "me" 或 "ex", "text": "消息内容", "time": "时间（如有）", "type": "text|emoji|image|voice|recall"},
  ...
]

只输出 JSON，不要其他文字。"""

    def __init__(self, config: dict):
        self.config = config
        self.mimo_config = config.get("mimo", {})

    def recognize(self, image_path: Path) -> list[dict]:
        """通过 MIMO Omni 识别，返回消息列表"""
        prompt = self.DEFAULT_PROMPT

        # 尝试 mimo_api.sh
        script_path = Path.home() / ".openclaw" / "skills" / "mimo-omni" / "mimo_api.sh"
        if script_path.exists():
            try:
                result = subprocess.run(
                    ["bash", str(script_path), "image", str(image_path), prompt],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    return self._parse_json(result.stdout.strip())
            except Exception as e:
                console.print(f"[yellow]MIMO Omni 失败: {e}[/yellow]")

        # Fallback: 直接 API
        return self._call_api_direct(image_path, prompt)

    def _call_api_direct(self, image_path: Path, prompt: str) -> list[dict]:
        """直接调用 API"""
        import base64
        import asyncio
        import aiohttp

        api_key = self.mimo_config.get("api_key", "")
        endpoint = self.mimo_config.get("endpoint", "")

        if not api_key or not endpoint:
            raise ValueError("MIMO API 配置缺失")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = image_path.suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime = mime_map.get(ext, "image/png")

        payload = {
            "model": "mimo-v2.5-pro",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}}
            ]}]
        }

        async def _fetch():
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]

        raw = asyncio.run(_fetch())
        return self._parse_json(raw)

    def _parse_json(self, text: str) -> list[dict]:
        """解析 JSON 输出"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                elif line.startswith("```") and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        try:
            messages = json.loads(text)
            if isinstance(messages, list):
                for msg in messages:
                    msg["engine"] = self.name
                return messages
        except json.JSONDecodeError:
            pass
        return []


class MultiEngineOCR:
    """多引擎融合 OCR — 多引擎投票提高准确率"""

    def __init__(self, config: dict, engines: list[str] = None):
        self.config = config
        self.engine_names = engines or ["mimo_omni"]
        self._engines = {}

    def _init_engine(self, name: str) -> OCREngine:
        if name in self._engines:
            return self._engines[name]

        engines = {
            "paddleocr": lambda: PaddleOCREngine(),
            "easyocr": lambda: EasyOCREngine(),
            "mimo_omni": lambda: MIMOOmniEngine(self.config),
        }

        if name not in engines:
            raise ValueError(f"未知引擎: {name}，可选: {list(engines.keys())}")

        engine = engines[name]()
        self._engines[name] = engine
        return engine

    def recognize(self, image_path: Path, primary: str = None) -> list[dict]:
        """使用多引擎识别，返回融合结果"""
        primary = primary or self.engine_names[0]

        # 主引擎
        main_engine = self._init_engine(primary)
        results = main_engine.recognize(image_path)

        if not results and len(self.engine_names) > 1:
            # 主引擎失败，尝试备用
            for alt_name in self.engine_names[1:]:
                console.print(f"[yellow]主引擎 {primary} 无结果，尝试 {alt_name}...[/yellow]")
                alt_engine = self._init_engine(alt_name)
                results = alt_engine.recognize(image_path)
                if results:
                    break

        return results

    def recognize_all_engines(self, image_path: Path) -> dict[str, list[dict]]:
        """所有引擎分别识别，返回各引擎结果"""
        all_results = {}
        for name in self.engine_names:
            engine = self._init_engine(name)
            try:
                all_results[name] = engine.recognize(image_path)
            except Exception as e:
                console.print(f"[yellow]{name} 失败: {e}[/yellow]")
                all_results[name] = []
        return all_results
