#!/usr/bin/env python3
"""
记忆层 — 滑动窗口 + 关键事件记忆
让"前任"有记忆，对话更立体
"""

import json
import time
from collections import deque
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class MemorySlot:
    """单条记忆"""
    def __init__(self, content: str, importance: float = 0.5, timestamp: float = None):
        self.content = content
        self.importance = importance  # 0.0 ~ 1.0
        self.timestamp = timestamp or time.time()
        self.access_count = 0
        self.last_accessed = self.timestamp

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemorySlot":
        slot = cls(data["content"], data["importance"], data["timestamp"])
        slot.access_count = data.get("access_count", 0)
        slot.last_accessed = data.get("last_accessed", slot.timestamp)
        return slot


class MemoryLayer:
    """
    记忆层 — 三层架构:
    1. 滑动窗口 (短期): 最近 N 轮对话，即时上下文
    2. 关键事件 (中期): 被标记为重要的事件
    3. 持久记忆 (长期): 序列化到文件，跨会话保存
    """

    def __init__(self, config: dict, memory_dir: str = "data/memory"):
        self.config = config
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 1. 滑动窗口 — 最近 N 轮
        self.window_size = config.get("memory", {}).get("window_size", 10)
        self.sliding_window: deque[dict] = deque(maxlen=self.window_size * 2)  # *2 因为包含 user+assistant

        # 2. 关键事件记忆
        self.key_events: list[MemorySlot] = []
        self.max_key_events = config.get("memory", {}).get("max_key_events", 50)

        # 3. 持久记忆文件
        self.memory_file = self.memory_dir / "long_term.json"

        # 加载长期记忆
        self._load_long_term()

    def _load_long_term(self):
        """加载长期记忆"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.key_events = [MemorySlot.from_dict(d) for d in data.get("key_events", [])]
                console.print(f"[dim]加载 {len(self.key_events)} 条长期记忆[/dim]")
            except Exception:
                pass

    def _save_long_term(self):
        """保存长期记忆"""
        data = {
            "key_events": [m.to_dict() for m in self.key_events[-self.max_key_events:]],
            "updated_at": time.time(),
        }
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_conversation(self, user_msg: str, assistant_msg: str):
        """添加对话到滑动窗口"""
        self.sliding_window.append({"role": "user", "content": user_msg, "time": time.time()})
        self.sliding_window.append({"role": "assistant", "content": assistant_msg, "time": time.time()})

    def add_key_event(self, content: str, importance: float = 0.7):
        """添加关键事件记忆"""
        # 去重：如果已有类似内容，更新而非重复添加
        for slot in self.key_events:
            if self._similarity(slot.content, content) > 0.8:
                slot.importance = max(slot.importance, importance)
                slot.access_count += 1
                slot.last_accessed = time.time()
                self._save_long_term()
                return

        slot = MemorySlot(content, importance)
        self.key_events.append(slot)

        # 按重要性排序，保留 top N
        self.key_events.sort(key=lambda s: s.importance, reverse=True)
        self.key_events = self.key_events[:self.max_key_events]

        self._save_long_term()
        console.print(f"[dim]新记忆: {content[:50]}... (重要性: {importance})[/dim]")

    def get_context_messages(self, max_messages: int = None) -> list[dict]:
        """获取滑动窗口中的对话（用于 LLM 上下文）"""
        max_messages = max_messages or self.window_size * 2
        messages = list(self.sliding_window)[-max_messages:]
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def get_key_memories(self, top_n: int = 5) -> list[str]:
        """获取最重要的 N 条关键记忆"""
        # 按重要性 * 访问频率加权
        scored = []
        for slot in self.key_events:
            recency = time.time() - slot.last_accessed
            score = slot.importance * (1 + slot.access_count * 0.1) * (1 / (1 + recency / 86400))
            scored.append((score, slot))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1].content for s in scored[:top_n]]

    def build_memory_prompt(self) -> str:
        """构建记忆提示词（注入到 system prompt）"""
        memories = self.get_key_memories(5)
        if not memories:
            return ""

        lines = ["## 你记得的事情（关键记忆）"]
        for i, m in enumerate(memories, 1):
            lines.append(f"{i}. {m}")
        return "\n".join(lines)

    def _similarity(self, a: str, b: str) -> float:
        """简单文本相似度（字符重叠率）"""
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        overlap = len(set_a & set_b)
        return overlap / max(len(set_a), len(set_b))

    def summarize_and_extract(self, messages: list[dict], llm_func=None) -> list[str]:
        """
        从对话中提取关键事件
        如果有 llm_func，用 LLM 提取；否则用规则提取
        """
        events = []

        if llm_func:
            # LLM 提取（更准确）
            prompt = "从以下对话中提取 3-5 个关键事件或重要信息点。\n"
            prompt += "只输出 JSON 数组，每项是一个简短描述（15字以内）。\n\n"
            prompt += "对话：\n"
            for m in messages[-20:]:
                speaker = "我" if m["role"] == "user" else "TA"
                prompt += f"{speaker}: {m['content']}\n"
            prompt += '\n输出示例：["约好周末看电影", "TA说想吃火锅", "吵架了但和好了"]'

            try:
                import asyncio
                result = asyncio.run(llm_func(prompt))
                events = json.loads(result)
            except Exception:
                pass

        if not events:
            # 规则提取（备用）
            for msg in messages:
                text = msg["content"]
                # 提取包含时间/地点/事件的句子
                if any(kw in text for kw in ["约", "周末", "明天", "晚上", "一起", "想去", "生日", "纪念"]):
                    events.append(text[:30])
                # 提取情感信号
                if any(kw in text for kw in ["生气", "开心", "想你", "难过", "爱", "讨厌", "感动"]):
                    events.append(text[:30])

        return events[:5]

    def stats(self) -> dict:
        """记忆状态统计"""
        return {
            "sliding_window": len(self.sliding_window),
            "key_events": len(self.key_events),
            "memory_file": str(self.memory_file),
            "file_exists": self.memory_file.exists(),
        }
