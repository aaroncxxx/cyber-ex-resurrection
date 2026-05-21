#!/usr/bin/env python3
"""
情感分析引擎 — 检测对话情绪 + 生成情感化回复
"""

import json
import re
from typing import Optional
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


# ─────────────────────────────────────────────
# 情感词典
# ─────────────────────────────────────────────
EMOTION_LEXICON = {
    "joy": {
        "keywords": ["开心", "高兴", "哈哈", "嘿嘿", "嘻嘻", "太好了", "棒", "赞",
                     "喜欢", "爱", "快乐", "幸福", "兴奋", "期待", "惊喜", "完美",
                     "厉害", "牛", "强", "绝了", "笑死", "😂", "🤣", "😊", "😄",
                     "🥰", "😍", "❤️", "💕", "🎉", "🥳", "太棒了", "好耶"],
        "emoji": ["😂", "🤣", "😊", "😄", "🥰", "😍", "❤️", "💕", "🎉", "🥳"],
        "intensity": 0.8,
    },
    "sadness": {
        "keywords": ["难过", "伤心", "哭", "😢", "😭", "委屈", "心疼", "可怜",
                     "寂寞", "孤独", "想你", "思念", "不舍", "遗憾", "无奈",
                     "唉", "哎", "烦", "郁闷", "无聊", "😞", "😔", "😟", "😿"],
        "emoji": ["😢", "😭", "😞", "😔", "😟", "😿", "💔"],
        "intensity": 0.7,
    },
    "anger": {
        "keywords": ["生气", "气死", "愤怒", "烦死", "讨厌", "滚", "闭嘴", "够了",
                     "受不了", "忍不了", "太过分", "混蛋", "白痴", "神经病",
                     "😡", "🤬", "😤", "💢", "无语", "服了", "醉了"],
        "emoji": ["😡", "🤬", "😤", "💢", "👿"],
        "intensity": 0.9,
    },
    "surprise": {
        "keywords": ["天哪", "我靠", "卧槽", "真的吗", "不会吧", "啊", "哇",
                     "震惊", "惊了", "没想到", "居然", "竟然", "意外",
                     "😲", "😱", "🤯", "😳", "啊这"],
        "emoji": ["😲", "😱", "🤯", "😳", "❗", "❓"],
        "intensity": 0.7,
    },
    "fear": {
        "keywords": ["害怕", "恐惧", "吓", "怕", "担心", "紧张", "不安",
                     "焦虑", "慌", "心虚", "忐忑", "😰", "😨", "😱"],
        "emoji": ["😰", "😨", "😱", "🫣"],
        "intensity": 0.6,
    },
    "disgust": {
        "keywords": ["恶心", "呕", "讨厌", "嫌弃", "恶", "🤮", "🤢",
                     "受不了", "看不下去", "过分", "离谱"],
        "emoji": ["🤮", "🤢", "😑"],
        "intensity": 0.7,
    },
    "love": {
        "keywords": ["爱你", "想你", "喜欢你", "亲亲", "抱抱", "么么", "宝贝",
                     "亲爱的", "想见你", "离不开", "永远", "一辈子",
                     "😘", "🥰", "😍", "💗", "💖", "💝", "💋", "🫶"],
        "emoji": ["😘", "🥰", "😍", "💗", "💖", "💝", "💋", "🫶", "❤️"],
        "intensity": 0.9,
    },
    "teasing": {
        "keywords": ["嘿嘿", "嘻嘻", "略略略", "就不", "偏不", "气你", "逗你",
                     "笨蛋", "傻瓜", "猪", "呆子", "憨憨", "😏", "😜", "😝"],
        "emoji": ["😏", "😜", "😝", "🤪", "😈"],
        "intensity": 0.6,
    },
    "neutral": {
        "keywords": [],
        "emoji": [],
        "intensity": 0.3,
    },
}

# 情感回复模板
EMOTION_RESPONSE_HINTS = {
    "joy": "用开心的语气回复，可以一起开心，用 TA 常用的开心 emoji",
    "sadness": "用温柔体贴的语气回复，表达关心和陪伴，不要太正能量",
    "anger": "如果是生别人的气，一起吐槽；如果是生用户的气，适当道歉或安抚",
    "surprise": "用惊讶的语气回复，配合 TA 的惊讶习惯",
    "fear": "用安抚的语气回复，给 TA 安全感",
    "disgust": "一起吐槽或表达理解",
    "love": "用甜蜜的语气回复，保持 TA 的风格",
    "teasing": "用调皮的语气回复，保持互动感",
    "neutral": "正常对话，保持 TA 的风格",
}


@dataclass
class EmotionState:
    """情感状态"""
    primary: str = "neutral"           # 主要情绪
    intensity: float = 0.3             # 强度 0~1
    secondary: str = None              # 次要情绪
    valence: float = 0.0               # 效价 -1(消极) ~ +1(积极)
    arousal: float = 0.0               # 唤醒度 0(平静) ~ 1(激动)
    emojis: list = field(default_factory=list)  # 匹配的 emoji
    keywords_found: list = field(default_factory=list)  # 匹配的关键词

    def to_dict(self) -> dict:
        return {
            "primary": self.primary,
            "intensity": round(self.intensity, 2),
            "secondary": self.secondary,
            "valence": round(self.valence, 2),
            "arousal": round(self.arousal, 2),
            "emojis": self.emojis,
            "keywords_found": self.keywords_found[:5],
        }

    def to_prompt_hint(self) -> str:
        """生成情感提示词"""
        hint = EMOTION_RESPONSE_HINTS.get(self.primary, "")
        if self.intensity > 0.7:
            hint += "（情绪强烈，需要更明显的情感回应）"
        elif self.intensity < 0.3:
            hint += "（情绪平缓，正常回复即可）"
        return hint


class EmotionAnalyzer:
    """情感分析器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.mimo_config = config.get("mimo", {}) if config else {}
        self._history: list[EmotionState] = []

    def analyze_text(self, text: str) -> EmotionState:
        """基于词典的情感分析"""
        text_lower = text.lower()
        scores = {}
        matched_keywords = {}

        for emotion, data in EMOTION_LEXICON.items():
            if emotion == "neutral":
                continue
            score = 0
            keywords = []
            for kw in data["keywords"]:
                count = text_lower.count(kw.lower())
                if count > 0:
                    score += count * data["intensity"]
                    keywords.append(kw)
            # Emoji 匹配
            for emoji in data["emoji"]:
                if emoji in text:
                    score += 0.5
                    keywords.append(emoji)

            if score > 0:
                scores[emotion] = score
                matched_keywords[emotion] = keywords

        if not scores:
            return EmotionState(primary="neutral", intensity=0.3)

        # 排序
        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_emotions[0]
        secondary = sorted_emotions[1][0] if len(sorted_emotions) > 1 else None

        # 计算效价和唤醒度
        valence_map = {
            "joy": 0.8, "love": 0.9, "teasing": 0.4,
            "sadness": -0.7, "anger": -0.6, "disgust": -0.5,
            "fear": -0.4, "surprise": 0.1, "neutral": 0.0,
        }
        arousal_map = {
            "joy": 0.6, "love": 0.7, "teasing": 0.5,
            "sadness": 0.3, "anger": 0.9, "disgust": 0.5,
            "fear": 0.7, "surprise": 0.8, "neutral": 0.2,
        }

        state = EmotionState(
            primary=primary[0],
            intensity=min(primary[1] / 5.0, 1.0),
            secondary=secondary,
            valence=valence_map.get(primary[0], 0.0),
            arousal=arousal_map.get(primary[0], 0.3),
            emojis=EMOTION_LEXICON.get(primary[0], {}).get("emoji", []),
            keywords_found=matched_keywords.get(primary[0], []),
        )

        self._history.append(state)
        return state

    def analyze_conversation(self, messages: list[dict]) -> list[EmotionState]:
        """分析整段对话的情感轨迹"""
        states = []
        for msg in messages:
            text = msg.get("text", "") or msg.get("content", "")
            if text:
                state = self.analyze_text(text)
                states.append(state)
        return states

    def get_emotion_trajectory(self, window: int = 10) -> dict:
        """获取情感轨迹（最近 N 条）"""
        recent = self._history[-window:] if self._history else []
        if not recent:
            return {"dominant": "neutral", "trend": "stable", "states": []}

        # 主导情绪
        from collections import Counter
        emotions = Counter(s.primary for s in recent)
        dominant = emotions.most_common(1)[0][0]

        # 趋势：效价变化
        if len(recent) >= 3:
            early_valence = sum(s.valence for s in recent[:len(recent)//2]) / (len(recent)//2)
            late_valence = sum(s.valence for s in recent[len(recent)//2:]) / (len(recent) - len(recent)//2)
            diff = late_valence - early_valence
            if diff > 0.2:
                trend = "improving"
            elif diff < -0.2:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "dominant": dominant,
            "trend": trend,
            "states": [s.to_dict() for s in recent],
        }

    def generate_emotion_prompt(self, state: EmotionState) -> str:
        """生成情感感知的提示词"""
        hint = state.to_prompt_hint()
        trajectory = self.get_emotion_trajectory()

        parts = [f"## 情感感知\n\n当前情绪: {state.primary} (强度: {state.intensity:.1f})"]
        if state.secondary:
            parts.append(f"次要情绪: {state.secondary}")
        parts.append(f"效价: {'积极' if state.valence > 0 else '消极' if state.valence < 0 else '中性'}")
        parts.append(f"回复指引: {hint}")

        if trajectory["trend"] != "stable":
            trend_cn = {"improving": "情绪好转中", "declining": "情绪变差中"}
            parts.append(f"情感趋势: {trend_cn.get(trajectory['trend'], trajectory['trend'])}")

        return "\n".join(parts)

    async def analyze_with_llm(self, text: str) -> EmotionState:
        """用 LLM 进行深度情感分析（可选）"""
        api_key = self.mimo_config.get("api_key", "")
        endpoint = self.mimo_config.get("endpoint", "")

        if not api_key or not endpoint:
            return self.analyze_text(text)

        import aiohttp

        prompt = f"""分析以下消息的情感状态，输出 JSON：

消息: "{text}"

输出格式:
{{"primary": "joy/sadness/anger/surprise/fear/love/teasing/neutral", "intensity": 0.0-1.0, "valence": -1.0到1.0, "arousal": 0.0-1.0}}

只输出 JSON，不要其他文字。"""

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "mimo-v2.5-pro",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 100,
                }
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    data = await resp.json()
                    result = json.loads(data["choices"][0]["message"]["content"])

                    state = EmotionState(
                        primary=result.get("primary", "neutral"),
                        intensity=result.get("intensity", 0.3),
                        valence=result.get("valence", 0.0),
                        arousal=result.get("arousal", 0.3),
                        emojis=EMOTION_LEXICON.get(result.get("primary", "neutral"), {}).get("emoji", []),
                    )
                    self._history.append(state)
                    return state
        except Exception:
            return self.analyze_text(text)
