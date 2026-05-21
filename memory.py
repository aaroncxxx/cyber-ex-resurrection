#!/usr/bin/env python3
"""
记忆层 v3 — 四层架构 + RAG 向量检索

四层记忆:
1. 滑动窗口 (短期): 最近 N 轮对话，即时上下文
2. 关键事件 (中期): 被标记为重要的事件
3. 持久记忆 (长期): 序列化到文件，跨会话保存
4. 向量记忆 (RAG): 基于语义检索的历史记忆
"""

import json
import time
from collections import Counter, deque
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class MemorySlot:
    """单条记忆"""
    def __init__(self, content: str, importance: float = 0.5, timestamp: float = None,
                 category: str = "general", emotion: str = None):
        self.content = content
        self.importance = importance
        self.timestamp = timestamp or time.time()
        self.access_count = 0
        self.last_accessed = self.timestamp
        self.category = category  # general/preference/event/emotion/relationship
        self.emotion = emotion    # 关联的情绪

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "category": self.category,
            "emotion": self.emotion,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemorySlot":
        slot = cls(
            data["content"],
            data["importance"],
            data["timestamp"],
            data.get("category", "general"),
            data.get("emotion"),
        )
        slot.access_count = data.get("access_count", 0)
        slot.last_accessed = data.get("last_accessed", slot.timestamp)
        return slot


class MemoryLayer:
    """
    记忆层 v3 — 四层架构 + RAG

    1. 滑动窗口: 最近 N 轮对话
    2. 关键事件: 重要事件记忆
    3. 持久记忆: 跨会话保存
    4. 向量记忆: RAG 语义检索
    """

    def __init__(self, config: dict, memory_dir: str = "data/memory"):
        self.config = config
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 1. 滑动窗口
        self.window_size = config.get("memory", {}).get("window_size", 10)
        self.sliding_window: deque[dict] = deque(maxlen=self.window_size * 2)

        # 2. 关键事件
        self.key_events: list[MemorySlot] = []
        self.max_key_events = config.get("memory", {}).get("max_key_events", 50)

        # 3. 持久记忆
        self.memory_file = self.memory_dir / "long_term.json"

        # 4. 用户偏好记忆
        self.preferences: dict = {
            "likes": [],      # 喜欢的东西
            "dislikes": [],   # 不喜欢的东西
            "habits": [],     # 习惯
            "important_dates": [],  # 重要日期
            "relationships": {},    # 人际关系
        }
        self.pref_file = self.memory_dir / "preferences.json"

        # 加载
        self._load_long_term()
        self._load_preferences()

        # RAG（延迟初始化）
        self._rag = None

    @property
    def rag(self):
        """延迟初始化 RAG"""
        if self._rag is None:
            from rag_store import RAGStore
            self._rag = RAGStore(self.config, store_dir="data/rag")
        return self._rag

    def _load_long_term(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.key_events = [MemorySlot.from_dict(d) for d in data.get("key_events", [])]
                console.print(f"[dim]加载 {len(self.key_events)} 条长期记忆[/dim]")
            except Exception:
                pass

    def _save_long_term(self):
        data = {
            "key_events": [m.to_dict() for m in self.key_events[-self.max_key_events:]],
            "updated_at": time.time(),
        }
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_preferences(self):
        if self.pref_file.exists():
            try:
                with open(self.pref_file, "r", encoding="utf-8") as f:
                    self.preferences.update(json.load(f))
            except Exception:
                pass

    def _save_preferences(self):
        with open(self.pref_file, "w", encoding="utf-8") as f:
            json.dump(self.preferences, f, ensure_ascii=False, indent=2)

    def add_conversation(self, user_msg: str, assistant_msg: str):
        """添加对话到滑动窗口"""
        self.sliding_window.append({"role": "user", "content": user_msg, "time": time.time()})
        self.sliding_window.append({"role": "assistant", "content": assistant_msg, "time": time.time()})

    def add_key_event(self, content: str, importance: float = 0.7,
                      category: str = "event", emotion: str = None):
        """添加关键事件记忆"""
        # 去重
        for slot in self.key_events:
            if self._similarity(slot.content, content) > 0.8:
                slot.importance = max(slot.importance, importance)
                slot.access_count += 1
                slot.last_accessed = time.time()
                self._save_long_term()
                return

        slot = MemorySlot(content, importance, category=category, emotion=emotion)
        self.key_events.append(slot)
        self.key_events.sort(key=lambda s: s.importance, reverse=True)
        self.key_events = self.key_events[:self.max_key_events]
        self._save_long_term()
        console.print(f"[dim]新记忆 [{category}]: {content[:50]}...[/dim]")

    def add_preference(self, category: str, item: str):
        """添加用户偏好"""
        if category in self.preferences and isinstance(self.preferences[category], list):
            if item not in self.preferences[category]:
                self.preferences[category].append(item)
                self._save_preferences()

    def get_context_messages(self, max_messages: int = None) -> list[dict]:
        """获取滑动窗口中的对话"""
        max_messages = max_messages or self.window_size * 2
        messages = list(self.sliding_window)[-max_messages:]
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def get_key_memories(self, top_n: int = 5, category: str = None) -> list[str]:
        """获取最重要的 N 条关键记忆"""
        events = self.key_events
        if category:
            events = [e for e in events if e.category == category]

        scored = []
        for slot in events:
            recency = time.time() - slot.last_accessed
            score = slot.importance * (1 + slot.access_count * 0.1) * (1 / (1 + recency / 86400))
            scored.append((score, slot))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1].content for s in scored[:top_n]]

    def search_memory(self, query: str, top_k: int = 3) -> list[str]:
        """通过 RAG 检索相关记忆"""
        results = self.rag.search(query, top_k=top_k)
        return [doc.text for doc in results]

    def build_memory_prompt(self) -> str:
        """构建记忆提示词"""
        parts = []

        # 关键事件
        memories = self.get_key_memories(5)
        if memories:
            lines = ["## 你记得的事情（关键记忆）"]
            for i, m in enumerate(memories, 1):
                lines.append(f"{i}. {m}")
            parts.append("\n".join(lines))

        # 用户偏好
        prefs = []
        if self.preferences.get("likes"):
            prefs.append(f"喜欢: {', '.join(self.preferences['likes'][:5])}")
        if self.preferences.get("dislikes"):
            prefs.append(f"不喜欢: {', '.join(self.preferences['dislikes'][:5])}")
        if self.preferences.get("habits"):
            prefs.append(f"习惯: {', '.join(self.preferences['habits'][:5])}")
        if prefs:
            parts.append("## 用户偏好\n" + "\n".join(prefs))

        return "\n\n".join(parts)

    def build_rag_context(self, query: str) -> str:
        """构建 RAG 检索上下文"""
        results = self.search_memory(query, top_k=3)
        if not results:
            return ""
        lines = ["## 相关历史记忆（语义检索）"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r}")
        return "\n".join(lines)

    def summarize_and_extract(self, messages: list[dict], llm_func=None) -> list[dict]:
        """从对话中提取关键事件（增强版：带分类和情感）"""
        events = []

        if llm_func:
            prompt = """从以下对话中提取 3-5 个关键事件或重要信息点。

对每个事件，输出 JSON 对象：
- "content": 简短描述（15字以内）
- "category": event/preference/emotion/relationship
- "emotion": 关联情绪（如有）
- "importance": 0.5-1.0

输出 JSON 数组。对话：
"""
            for m in messages[-20:]:
                speaker = "我" if m["role"] == "user" else "TA"
                prompt += f"{speaker}: {m['content']}\n"
            prompt += '\n输出示例：[{"content":"约好周末看电影","category":"event","importance":0.8}]'

            try:
                import asyncio
                result = asyncio.run(llm_func(prompt))
                events = json.loads(result)
            except Exception:
                pass

        if not events:
            # 规则提取
            for msg in messages:
                text = msg["content"]
                if any(kw in text for kw in ["约", "周末", "明天", "晚上", "一起", "生日", "纪念"]):
                    events.append({"content": text[:30], "category": "event", "importance": 0.7})
                if any(kw in text for kw in ["喜欢", "讨厌", "爱", "最想", "最怕"]):
                    events.append({"content": text[:30], "category": "preference", "importance": 0.6})
                if any(kw in text for kw in ["生气", "开心", "想你", "难过", "感动"]):
                    events.append({"content": text[:30], "category": "emotion", "importance": 0.6})

        return events[:5]

    def _similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        return len(set_a & set_b) / max(len(set_a | set_b), 1)

    def stats(self) -> dict:
        return {
            "sliding_window": len(self.sliding_window),
            "key_events": len(self.key_events),
            "categories": dict(Counter(e.category for e in self.key_events)) if self.key_events else {},
            "preferences": {k: len(v) for k, v in self.preferences.items() if isinstance(v, list)},
            "memory_file": str(self.memory_file),
            "rag_stats": self.rag.get_stats() if self._rag else "未初始化",
        }

