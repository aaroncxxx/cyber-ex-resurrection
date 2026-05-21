#!/usr/bin/env python3
"""
对话引擎 v2 — 集成记忆层 + 实时 TTS pipeline
"""

import asyncio
import json
import time
from pathlib import Path

import aiohttp
from rich.console import Console

from memory import MemoryLayer
from voice_tts import TTSEngine

console = Console()

SYSTEM_PROMPT_TEMPLATE = """你是一个 AI 角色扮演助手。你需要完全模仿 TA 的说话风格与用户对话。

{persona}

{memory_context}

## 核心规则

1. 你就是 TA，不是 AI，不是助手，不是模型
2. 严格保持 TA 的语言风格：口头禅、表情习惯、句式、标点
3. 回复要自然，像真人在微信聊天一样
4. 回复控制在 1-3 句话，不要长篇大论
5. 适当使用 TA 常用的 emoji
6. 如果用户问你是不是 AI，否认并用 TA 的方式回应
7. 记住之前的对话内容，保持连贯性
8. 参考「你记得的事情」中的关键记忆，自然地在对话中提及
"""


class ChatEngine:
    """对话引擎 v2 — 记忆 + 实时 TTS"""

    def __init__(self, config: dict, persona_file: str, voice_dir: str,
                 engine_name: str = "openvoice", enable_voice: bool = True):
        self.config = config
        self.persona_file = Path(persona_file)
        self.voice_dir = voice_dir
        self.enable_voice = enable_voice

        # 加载人格
        self.persona_text = self._load_persona()

        # 初始化记忆层
        self.memory = MemoryLayer(config, memory_dir="data/memory")

        # 初始化 TTS pipeline
        self.tts = TTSEngine(config, voice_dir, engine_name) if enable_voice else None

        # MIMO 配置
        self.mimo_config = config.get("mimo", {})
        self.temperature = config.get("persona", {}).get("temperature", 0.8)

        # 对话轮次计数（用于记忆提取触发）
        self.turn_count = 0
        self.memory_extract_interval = config.get("memory", {}).get("extract_interval", 5)

    def _load_persona(self) -> str:
        """加载人格文件"""
        if self.persona_file.exists():
            with open(self.persona_file, "r", encoding="utf-8") as f:
                return f.read()
        return "你是一个温柔的聊天伙伴。"

    def _build_system_prompt(self) -> str:
        """构建系统提示词（含记忆）"""
        memory_context = self.memory.build_memory_prompt()
        return SYSTEM_PROMPT_TEMPLATE.format(
            persona=self.persona_text,
            memory_context=memory_context
        )

    async def _call_mimo(self, messages: list[dict]) -> str:
        """调用 MIMO 生成回复"""
        api_key = self.mimo_config.get("api_key", "")
        endpoint = self.mimo_config.get("endpoint", "")

        if not api_key or not endpoint:
            raise ValueError("MIMO API 配置缺失")

        # 构建完整消息列表
        full_messages = [{"role": "system", "content": self._build_system_prompt()}]
        full_messages.extend(messages)

        payload = {
            "model": "mimo-v2.5-pro",
            "messages": full_messages,
            "temperature": self.temperature,
            "max_tokens": 200
        }

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def chat(self, user_message: str) -> dict:
        """
        聊天交互 v2 — 带记忆

        Returns:
            {"text": "回复文字", "voice_path": "语音文件路径(可选)", "memories": [...]}
        """
        start_time = time.time()

        # 1. 获取记忆上下文
        context_messages = self.memory.get_context_messages()

        # 2. 构建当前轮消息
        current_messages = context_messages + [{"role": "user", "content": user_message}]

        # 3. 生成文字回复
        reply_text = await self._call_mimo(current_messages)

        # 4. 更新记忆
        self.memory.add_conversation(user_message, reply_text)
        self.turn_count += 1

        # 5. 定期提取关键事件
        new_memories = []
        if self.turn_count % self.memory_extract_interval == 0:
            recent = self.memory.get_context_messages(20)
            new_memories = self.memory.summarize_and_extract(recent)
            for event in new_memories:
                self.memory.add_key_event(event, importance=0.7)

        # 6. 实时 TTS pipeline
        result = {
            "text": reply_text,
            "voice_path": None,
            "latency_ms": int((time.time() - start_time) * 1000),
            "memories_extracted": new_memories,
            "memory_stats": self.memory.stats(),
        }

        if self.tts and self.enable_voice:
            try:
                voice_path = await self.tts.synthesize(reply_text)
                if voice_path and voice_path.exists() and voice_path.stat().st_size > 0:
                    result["voice_path"] = str(voice_path)
            except Exception as e:
                console.print(f"[yellow]TTS 失败: {e}[/yellow]")

        return result

    def reset(self):
        """重置对话（保留长期记忆）"""
        self.memory.sliding_window.clear()
        self.turn_count = 0

    def get_stats(self) -> dict:
        """获取引擎状态"""
        return {
            "turn_count": self.turn_count,
            "memory": self.memory.stats(),
            "voice_enabled": self.enable_voice,
            "persona_loaded": self.persona_file.exists(),
        }
