#!/usr/bin/env python3
"""
人格建模 v3 — 多维度 + RAG + 情感分析 + MIMO 推理

维度:
1. 性格特征 (personality)
2. 价值观 (values)
3. 兴趣爱好 (interests)
4. 说话习惯 (speaking_style)
5. 情感模式 (emotional_patterns)
6. 社交风格 (social_style)
"""

import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Optional

import aiohttp
from rich.console import Console

from rag_store import RAGStore
from emotion import EmotionAnalyzer

console = Console()


# ─────────────────────────────────────────────
# N-gram 语言风格统计（保留 v2 的核心逻辑）
# ─────────────────────────────────────────────

def extract_ngrams(messages: list[dict], n: int = 2, role: str = "ex") -> list[str]:
    """提取指定角色的 n-gram"""
    texts = [m["text"] for m in messages if m.get("role") == role]
    all_ngrams = []
    for text in texts:
        text = re.sub(r"[^\u4e00-\u9fff\w]", "", text)
        if n == 1:
            all_ngrams.extend(list(text))
        elif n == 2:
            all_ngrams.extend([text[i:i+2] for i in range(len(text)-1)])
        else:
            words = re.split(r"[，。！？、\s]+", text)
            words = [w for w in words if w]
            for i in range(len(words) - n + 1):
                all_ngrams.append("".join(words[i:i+n]))
    return all_ngrams


def analyze_style(messages: list[dict]) -> dict:
    """分析语言风格统计特征"""
    ex_msgs = [m for m in messages if m.get("role") == "ex"]
    me_msgs = [m for m in messages if m.get("role") == "me"]

    return {
        "ex_msg_count": len(ex_msgs),
        "me_msg_count": len(me_msgs),
        "ex_avg_len": sum(len(m["text"]) for m in ex_msgs) / max(len(ex_msgs), 1),
        "me_avg_len": sum(len(m["text"]) for m in me_msgs) / max(len(me_msgs), 1),
        "ex_emojis": _extract_emojis(ex_msgs),
        "me_emojis": _extract_emojis(me_msgs),
        "ex_top_words": Counter(extract_ngrams(messages, n=1, role="ex")).most_common(30),
        "me_top_words": Counter(extract_ngrams(messages, n=1, role="me")).most_common(30),
        "ex_top_bigrams": Counter(extract_ngrams(messages, n=2, role="ex")).most_common(20),
        "me_top_bigrams": Counter(extract_ngrams(messages, n=2, role="me")).most_common(20),
        "ex_punctuation": _analyze_punctuation(ex_msgs),
        "me_punctuation": _analyze_punctuation(me_msgs),
        "ex_sentence_patterns": _analyze_sentence_patterns(ex_msgs),
        "ex_length_dist": _length_distribution(ex_msgs),
        "ex_terms_of_endearment": _extract_terms(ex_msgs, me_msgs),
    }


def _extract_emojis(messages: list[dict]) -> list[tuple]:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F"
        "\U0000200D\U00002600-\U000026FF\U00002B50\U0000231A-\U0000231B"
        "\U00002328\U000023CF\U000023E9-\U000023F3\U000023F8-\U000023FA"
        "]+", flags=re.UNICODE
    )
    extra = re.compile(r"[❤️💕😍😊🥰😘😭🤔😤🥺😡💀😂🤣😅😆😉😋😎🤗🤩🥳😏😒😞😔😟😕🙁😣😖😫😩🥺😢😭😤😠😡🤬😈👿💀☠️💩🤡👹👺👻👽👾🤖😺😸😹😻😼😽🙀😿🙈🙉🙊💋💌💘💝💖💗💓💞💕💟❣️💔❤️🧡💛💚💙💜🖤🤍🤎💯💢💥💫💦💨]")
    all_emojis = []
    for m in messages:
        all_emojis.extend(emoji_pattern.findall(m["text"]))
        all_emojis.extend(extra.findall(m["text"]))
    return Counter(all_emojis).most_common(10)


def _analyze_punctuation(messages: list[dict]) -> dict:
    counts = {"！": 0, "？": 0, "~": 0, "。。。": 0, "！？": 0, "❤️": 0}
    for m in messages:
        for p in counts:
            counts[p] += m["text"].count(p)
    total = sum(counts.values()) or 1
    return {k: round(v / total, 2) for k, v in counts.items() if v > 0}


def _analyze_sentence_patterns(messages: list[dict]) -> dict:
    patterns = {"question": 0, "exclamation": 0, "ellipsis": 0, "short": 0, "medium": 0, "long": 0}
    for m in messages:
        text = m["text"]
        if "？" in text or "?" in text: patterns["question"] += 1
        if "！" in text or "!" in text: patterns["exclamation"] += 1
        if "..." in text or "…" in text: patterns["ellipsis"] += 1
        length = len(text)
        if length < 5: patterns["short"] += 1
        elif length < 15: patterns["medium"] += 1
        else: patterns["long"] += 1
    total = len(messages) or 1
    return {k: round(v / total, 2) for k, v in patterns.items()}


def _length_distribution(messages: list[dict]) -> list[int]:
    return sorted([len(m["text"]) for m in messages])


def _extract_terms(ex_msgs: list[dict], me_msgs: list[dict]) -> list[str]:
    patterns = [r"(?:^|[，。！？\s])(你|宝贝|亲爱的|老公|老婆|宝|崽|猪|笨蛋|傻瓜|臭宝|宝宝|乖乖|小可爱)"]
    terms = set()
    for m in ex_msgs:
        for p in patterns:
            terms.update(re.findall(p, m["text"]))
    return list(terms)


# ─────────────────────────────────────────────
# 多维度人格建模 Prompt
# ─────────────────────────────────────────────

MULTI_DIMENSION_PROMPT = """你是一个顶级人格心理学家和语言风格分析专家。请根据以下数据，为"TA"构建一个多维度的高保真人格模型。

## 聊天记录（原始数据）
{chat_log}

## 语言风格统计分析
{style_stats}

## 情感分析摘要
{emotion_summary}

## RAG 检索的相关记忆
{rag_context}

## 分析要求 — 多维度人格建模

### 1. 性格特征 (Big Five + MBTI 参考)
- 外向性 vs 内向性
- 开放性 vs 保守性
- 宜人性 vs 竞争性
- 神经质 vs 情绪稳定
- 尽责性 vs 随性
- 参考 MBTI 类型判断

### 2. 价值观
- 什么对 TA 来说最重要？（家庭/事业/自由/安全感/...）
- TA 的人生信条或处世态度
- TA 对感情的态度

### 3. 兴趣爱好
- 从对话中提取 TA 感兴趣的话题
- TA 的娱乐方式（游戏/追剧/运动/...）
- TA 的消费习惯或偏好

### 4. 说话习惯（基于统计数据）
- Top 5 口头禅（必须有数据支撑）
- 标点习惯（感叹号/波浪号/省略号的使用比例）
- 句式偏好（短句/长句/问句比例）
- emoji 使用习惯（最常用 emoji Top 5）
- 称呼方式
- 打字节奏（一条消息分几段发？还是一次性发完？）

### 5. 情感模式
- 情绪触发器：什么话题容易让 TA 开心/生气/难过？
- 情绪表达方式：TA 如何表达不同情绪？
- 情绪恢复模式：生气后怎么和好？难过时需要什么？
- 情感需求：TA 最需要什么情感支持？

### 6. 社交风格
- TA 在关系中的角色（主导/跟随/平等）
- TA 的沟通偏好（直接/含蓄/暗示）
- TA 的边界感（什么话题会回避？）

### 7. Few-shot 示例（核心！必须包含）
为以下 8 个场景各写 1-2 句 TA 风格的示例对话：

**场景 A — 日常闲聊**
TA 说: ___

**场景 B — 开心时**
TA 说: ___

**场景 C — 生气/委屈时**
TA 说: ___

**场景 D — 撒娇时**
TA 说: ___

**场景 E — 关心对方时**
TA 说: ___

**场景 F — 冷战/不想说话时**
TA 说: ___

**场景 G — 催对方回消息**
TA 说: ___

**场景 H — 晚安/告别**
TA 说: ___

### 8. System Prompt（给 AI 用）
基于以上所有维度，写一个完整的 system prompt，让 AI 能完美扮演 TA。
要求：
- 包含所有维度的人格描述
- 包含语言风格规则
- 包含情感表达模式
- 包含称呼方式和互动模式
- 包含 few-shot 示例（至少 5 组对话）
- 输出为 Markdown 格式"""


class PersonaBuilder:
    """人格建模器 v3 — 多维度 + RAG + 情感"""

    def __init__(self, config: dict):
        self.config = config
        self.mimo_config = config.get("mimo", {})

        # 初始化 RAG 知识库
        self.rag = RAGStore(config, store_dir="data/rag")

        # 初始化情感分析器
        self.emotion = EmotionAnalyzer(config)

    def _format_chat_log(self, messages: list[dict]) -> str:
        lines = []
        for msg in messages:
            role = "我" if msg.get("role") == "me" else "TA"
            lines.append(f"{role}: {msg.get('text', '')}")
        return "\n".join(lines)

    def _format_style_stats(self, stats: dict) -> str:
        lines = []
        lines.append(f"### 基本统计")
        lines.append(f"- TA 发言: {stats['ex_msg_count']} 条 | 我发言: {stats['me_msg_count']} 条")
        lines.append(f"- TA 平均长度: {stats['ex_avg_len']:.1f} 字 | 我平均长度: {stats['me_avg_len']:.1f} 字")

        lines.append(f"\n### TA 的高频 emoji")
        for emoji, count in stats["ex_emojis"]:
            lines.append(f"  {emoji} × {count}")

        lines.append(f"\n### TA 的高频字 (Top 10)")
        for word, count in stats["ex_top_words"][:10]:
            lines.append(f"  「{word}」× {count}")

        lines.append(f"\n### TA 的高频 bigram (Top 10，口头禅候选)")
        for bigram, count in stats["ex_top_bigrams"][:10]:
            lines.append(f"  「{bigram}」× {count}")

        lines.append(f"\n### TA 的标点习惯")
        for p, ratio in stats["ex_punctuation"].items():
            lines.append(f"  {p}: {ratio*100:.0f}%")

        lines.append(f"\n### TA 的句式偏好")
        for pattern, ratio in stats["ex_sentence_patterns"].items():
            label = {"question": "问句", "exclamation": "感叹句", "ellipsis": "省略句",
                     "short": "短句(<5字)", "medium": "中句(5-15字)", "long": "长句(>15字)"}[pattern]
            lines.append(f"  {label}: {ratio*100:.0f}%")

        if stats["ex_terms_of_endearment"]:
            lines.append(f"\n### TA 对我的称呼")
            lines.append(f"  {', '.join(stats['ex_terms_of_endearment'])}")

        dist = stats["ex_length_dist"]
        if dist:
            lines.append(f"\n### TA 的消息长度分布")
            lines.append(f"  最短: {dist[0]}字 | 最长: {dist[-1]}字 | 中位数: {dist[len(dist)//2]}字")

        return "\n".join(lines)

    def _analyze_emotions(self, messages: list[dict]) -> str:
        """分析对话情感并生成摘要"""
        ex_msgs = [m for m in messages if m.get("role") == "ex"]
        states = self.emotion.analyze_conversation(ex_msgs)

        if not states:
            return "无情感数据"

        # 统计情绪分布
        emotion_counts = Counter(s.primary for s in states)
        trajectory = self.emotion.get_emotion_trajectory(20)

        lines = ["### 情绪分布"]
        for emotion, count in emotion_counts.most_common():
            pct = int(count / len(states) * 100)
            lines.append(f"  {emotion}: {pct}%")

        lines.append(f"\n### 情感趋势")
        lines.append(f"  主导情绪: {trajectory['dominant']}")
        lines.append(f"  趋势: {trajectory['trend']}")

        # 情绪触发器分析
        lines.append(f"\n### 情绪触发器")
        for emotion in ["joy", "sadness", "anger", "love"]:
            matching = [s for s in states if s.primary == emotion]
            if matching:
                keywords = []
                for s in matching:
                    keywords.extend(s.keywords_found)
                top_kw = Counter(keywords).most_common(3)
                if top_kw:
                    kw_str = ", ".join([f'"{kw}"' for kw, _ in top_kw])
                    lines.append(f"  {emotion} 触发词: {kw_str}")

        return "\n".join(lines)

    async def _call_mimo(self, prompt: str) -> str:
        api_key = self.mimo_config.get("api_key", "")
        endpoint = self.mimo_config.get("endpoint", "")

        if not api_key or not endpoint:
            raise ValueError("MIMO API 配置缺失")

        payload = {
            "model": "mimo-v2.5-pro",
            "messages": [
                {"role": "system", "content": "你是一个顶级人格心理学家和语言风格分析专家。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8
        }

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def build(self, chat_file: Path) -> str:
        """构建多维度人格模型"""
        with open(chat_file, "r", encoding="utf-8") as f:
            messages = json.load(f)

        console.print(f"[cyan]加载 {len(messages)} 条消息[/cyan]")

        # Step 1: N-gram 统计
        console.print("[cyan]Step 1: 语言风格统计分析...[/cyan]")
        stats = analyze_style(messages)
        style_text = self._format_style_stats(stats)

        # Step 2: 情感分析
        console.print("[cyan]Step 2: 情感模式分析...[/cyan]")
        emotion_summary = self._analyze_emotions(messages)

        # Step 3: RAG 索引
        console.print("[cyan]Step 3: RAG 知识库索引...[/cyan]")
        chunk_count = self.rag.index_chat_messages(messages, chunk_size=5)
        rag_stats = self.rag.get_stats()
        console.print(f"[green]  索引 {chunk_count} 个文档块[/green]")

        # Step 4: RAG 检索相关上下文
        console.print("[cyan]Step 4: RAG 检索相关上下文...[/cyan]")
        rag_context = self.rag.search_for_context("性格 习惯 喜欢 讨厌 情感", top_k=5)

        # Step 5: 截断聊天记录
        chat_log = self._format_chat_log(messages)
        max_lines = self.config.get("persona", {}).get("max_chat_lines", 500)
        lines = chat_log.split("\n")
        if len(lines) > max_lines:
            chat_log = "\n".join(lines[-max_lines:])
            console.print(f"[yellow]聊天记录过长，截取最后 {max_lines} 行[/yellow]")

        # Step 6: 多维度人格建模
        console.print("[cyan]Step 5: 多维度人格建模 (MIMO)...[/cyan]")
        prompt = MULTI_DIMENSION_PROMPT.format(
            chat_log=chat_log,
            style_stats=style_text,
            emotion_summary=emotion_summary,
            rag_context=rag_context,
        )

        persona = await self._call_mimo(prompt)

        # 索引人格到 RAG
        self.rag.index_persona(persona)

        # 附加数据摘要
        persona += f"\n\n---\n\n## 📊 数据支撑（自动生成）\n\n"
        persona += f"### 语言风格统计\n```json\n{json.dumps(stats, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
        persona += f"### 情感分析\n```\n{emotion_summary}\n```\n\n"
        persona += f"### RAG 知识库\n```\n{json.dumps(rag_stats, ensure_ascii=False, indent=2)}\n```\n\n"
        persona += f"### 生成时间\n{time.strftime('%Y-%m-%d %H:%M:%S')}\n"

        # Header
        persona = f"""# 赛博前任人格模型 v3 — 多维度版

> 本文件由「复活吧我的赛博前任」自动生成
> 基于多维度人格建模 + RAG 检索增强 + 情感分析 + MIMO 推理
> 用于指导 AI 以 TA 的风格进行对话

---

{persona}

---

## 使用说明

1. 将本文件作为 system prompt 的一部分
2. Few-shot 示例直接作为 few-shot prompt 使用
3. 情感模式用于调整回复语气
4. RAG 知识库可用于实时检索相关记忆
"""

        return persona

    async def build_preview(self, chat_file: Path) -> dict:
        """构建预览版（不调用 LLM，仅统计分析）"""
        with open(chat_file, "r", encoding="utf-8") as f:
            messages = json.load(f)

        stats = analyze_style(messages)
        emotion_summary = self._analyze_emotions(messages)

        # RAG 索引
        self.rag.index_chat_messages(messages)

        return {
            "stats": stats,
            "emotion_summary": emotion_summary,
            "rag_stats": self.rag.get_stats(),
            "sample_bigrams": [b for b, _ in stats["ex_top_bigrams"][:5]],
            "sample_emojis": [e for e, _ in stats["ex_emojis"][:5]],
        }
