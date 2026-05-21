#!/usr/bin/env python3
"""
人格建模 v2 — few-shot prompting + n-gram 语言风格统计
"""

import json
import re
from collections import Counter
from pathlib import Path

import aiohttp
from rich.console import Console

console = Console()

# ─────────────────────────────────────────────
# Step 1: N-gram 语言风格统计
# ─────────────────────────────────────────────

def extract_ngrams(messages: list[dict], n: int = 2, role: str = "ex") -> list[str]:
    """提取指定角色的 n-gram"""
    texts = [m["text"] for m in messages if m.get("role") == role]
    all_ngrams = []
    for text in texts:
        # 中文按字做 bigram，按词做 trigram+
        text = re.sub(r"[^\u4e00-\u9fff\w]", "", text)
        if n == 1:
            all_ngrams.extend(list(text))
        elif n == 2:
            all_ngrams.extend([text[i:i+2] for i in range(len(text)-1)])
        else:
            # 按标点分词后做 n-gram
            words = re.split(r"[，。！？、\s]+", text)
            words = [w for w in words if w]
            for i in range(len(words) - n + 1):
                all_ngrams.append("".join(words[i:i+n]))
    return all_ngrams


def analyze_style(messages: list[dict]) -> dict:
    """分析语言风格统计特征"""
    ex_msgs = [m for m in messages if m.get("role") == "ex"]
    me_msgs = [m for m in messages if m.get("role") == "me"]

    stats = {
        # 基本统计
        "ex_msg_count": len(ex_msgs),
        "me_msg_count": len(me_msgs),

        # 长度分布
        "ex_avg_len": sum(len(m["text"]) for m in ex_msgs) / max(len(ex_msgs), 1),
        "me_avg_len": sum(len(m["text"]) for m in me_msgs) / max(len(me_msgs), 1),

        # 高频 emoji
        "ex_emojis": _extract_emojis(ex_msgs),
        "me_emojis": _extract_emojis(me_msgs),

        # 高频词（unigram）
        "ex_top_words": Counter(extract_ngrams(messages, n=1, role="ex")).most_common(30),
        "me_top_words": Counter(extract_ngrams(messages, n=1, role="me")).most_common(30),

        # 高频 bigram（口头禅检测）
        "ex_top_bigrams": Counter(extract_ngrams(messages, n=2, role="ex")).most_common(20),
        "me_top_bigrams": Counter(extract_ngrams(messages, n=2, role="me")).most_common(20),

        # 标点习惯
        "ex_punctuation": _analyze_punctuation(ex_msgs),
        "me_punctuation": _analyze_punctuation(me_msgs),

        # 句式偏好
        "ex_sentence_patterns": _analyze_sentence_patterns(ex_msgs),

        # 消息间隔风格（短句 vs 长句）
        "ex_length_dist": _length_distribution(ex_msgs),

        # 称呼方式
        "ex_terms_of_endearment": _extract_terms(ex_msgs, me_msgs),
    }

    return stats


def _extract_emojis(messages: list[dict]) -> list[tuple]:
    """提取高频 emoji"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U0000FE00-\U0000FE0F"
        "\U0000200D"
        "\U00002600-\U000026FF"
        "\U00002B50"
        "\U0000231A-\U0000231B"
        "\U00002328"
        "\U000023CF"
        "\U000023E9-\U000023F3"
        "\U000023F8-\U000023FA"
        "]+",
        flags=re.UNICODE
    )
    # 也匹配常见 emoji 字符
    extra_emojis = re.compile(r"[❤️💕😍😊🥰😘😭🤔😤🥺😡💀😂🤣😅😆😉😋😎🤗🤩🥳😏😒😞😔😟😕🙁😣😖😫😩🥺😢😭😤😠😡🤬😈👿💀☠️💩🤡👹👺👻👽👾🤖😺😸😹😻😼😽🙀😿🙈🙉🙊💋💌💘💝💖💗💓💞💕💟❣️💔❤️🧡💛💚💙💜🖤🤍🤎💯💢💥💫💦💨🕳️💬👋🤚🖐️✋🖖👌🤌🤏✌️🤞🤟🤘🤙👈👉👆🖕👇☝️👍👎✊👊🤛🤜👏🙌👐🤲🤝🙏✍️💅🤳💪🦾🦿🦵🦶👂🦻👃🧠🫀🫁🦷🦴👀👁️👅👄👶🧒👦👧🧑👱👨🧔👩🧓👴👵🙍🙍‍♂️🙍‍♀️🙎🙎‍♂️🙎‍♀️🙅🙅‍♂️🙅‍♀️🙆🙆‍♂️🙆‍♀️💁💁‍♂️💁‍♀️🙋🙋‍♂️🙋‍♀️🧏🧏‍♂️🧏‍♀️🙇🙇‍♂️🙇‍♀️🤦🤦‍♂️🤦‍♀️🤷🤷‍♂️🤷‍♀️]")
    all_emojis = []
    for m in messages:
        all_emojis.extend(emoji_pattern.findall(m["text"]))
        all_emojis.extend(extra_emojis.findall(m["text"]))
    return Counter(all_emojis).most_common(10)


def _analyze_punctuation(messages: list[dict]) -> dict:
    """标点习惯分析"""
    counts = {"！": 0, "？": 0, "~": 0, "。。。": 0, "。。。": 0, "！？": 0, "❤️": 0}
    for m in messages:
        text = m["text"]
        for p in counts:
            counts[p] += text.count(p)

    total = sum(counts.values()) or 1
    return {k: round(v / total, 2) for k, v in counts.items() if v > 0}


def _analyze_sentence_patterns(messages: list[dict]) -> dict:
    """句式偏好分析"""
    patterns = {
        "question": 0,      # 问句
        "exclamation": 0,   # 感叹句
        "ellipsis": 0,      # 省略句
        "short": 0,         # 短句 (<5字)
        "medium": 0,        # 中句 (5-15字)
        "long": 0,          # 长句 (>15字)
    }
    for m in messages:
        text = m["text"]
        if "？" in text or "?" in text:
            patterns["question"] += 1
        if "！" in text or "!" in text:
            patterns["exclamation"] += 1
        if "..." in text or "…" in text or "。。。" in text:
            patterns["ellipsis"] += 1
        length = len(text)
        if length < 5:
            patterns["short"] += 1
        elif length < 15:
            patterns["medium"] += 1
        else:
            patterns["long"] += 1

    total = len(messages) or 1
    return {k: round(v / total, 2) for k, v in patterns.items()}


def _length_distribution(messages: list[dict]) -> list[int]:
    """消息长度分布"""
    return sorted([len(m["text"]) for m in messages])


def _extract_terms(ex_msgs: list[dict], me_msgs: list[dict]) -> list[str]:
    """提取对方对'我'的称呼"""
    # 从对方消息中找可能的称呼词
    term_patterns = [
        r"(?:^|[，。！？\s])(你|宝贝|亲爱的|老公|老婆|宝|崽|猪|笨蛋|傻瓜|臭宝|宝宝|乖乖|小可爱)",
    ]
    terms = set()
    for m in ex_msgs:
        for pattern in term_patterns:
            matches = re.findall(pattern, m["text"])
            terms.update(matches)
    return list(terms)


# ─────────────────────────────────────────────
# Step 2: Few-shot Prompt 构建
# ─────────────────────────────────────────────

FEW_SHOT_PROMPT = """你是一个语言风格分析专家。请根据以下数据，为"TA"构建一个高保真的人格模型。

## 聊天记录（原始数据）
{chat_log}

## 语言风格统计分析
{style_stats}

## 分析要求

### 1. 基于统计的风格画像
- 根据 n-gram 高频词提取口头禅（Top 5 口头禅必须有数据支撑）
- 根据标点统计确定语气习惯（爱用感叹号？波浪号？省略号？）
- 根据句式分布确定说话节奏（短句多=干脆？长句多=话痨？问句多=粘人？）
- 根据 emoji 统计确定表情习惯

### 2. Few-shot 示例（核心！必须包含）
为以下 8 个场景各写 1-2 句 TA 风格的示例对话，必须像真人说的：

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

### 3. System Prompt（给 AI 用）
基于以上分析，写一个完整的 system prompt，让 AI 能完美扮演 TA。
要求：
- 包含性格描述
- 包含语言风格规则（口头禅、标点、句式）
- 包含情感表达模式
- 包含称呼方式
- 包含 few-shot 示例（至少 5 组对话）
- 输出为 Markdown 格式"""


class PersonaBuilder:
    """人格建模器 v2 — few-shot + n-gram"""

    def __init__(self, config: dict):
        self.config = config
        self.mimo_config = config.get("mimo", {})

    def _format_chat_log(self, messages: list[dict]) -> str:
        """格式化聊天记录为文本"""
        lines = []
        for msg in messages:
            role = "我" if msg.get("role") == "me" else "TA"
            text = msg.get("text", "")
            lines.append(f"{role}: {text}")
        return "\n".join(lines)

    def _format_style_stats(self, stats: dict) -> str:
        """格式化风格统计为可读文本"""
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

        lines.append(f"\n### TA 的消息长度分布")
        dist = stats["ex_length_dist"]
        if dist:
            lines.append(f"  最短: {dist[0]}字 | 最长: {dist[-1]}字 | 中位数: {dist[len(dist)//2]}字")

        return "\n".join(lines)

    async def _call_mimo(self, prompt: str) -> str:
        """调用 MIMO LLM"""
        api_key = self.mimo_config.get("api_key", "")
        endpoint = self.mimo_config.get("endpoint", "")

        if not api_key or not endpoint:
            raise ValueError("MIMO API 配置缺失，请在 config.json 中配置 mimo.api_key 和 mimo.endpoint")

        payload = {
            "model": "mimo-v2.5-pro",
            "messages": [
                {"role": "system", "content": "你是一个专业的语言风格分析师，擅长从对话数据中提取人格特征并生成高保真的角色扮演 prompt。"},
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
        """构建人格模型 v2"""
        with open(chat_file, "r", encoding="utf-8") as f:
            messages = json.load(f)

        console.print(f"[cyan]加载 {len(messages)} 条消息[/cyan]")

        # Step 1: N-gram 统计分析
        console.print("[cyan]Step 1: 语言风格统计分析...[/cyan]")
        stats = analyze_style(messages)
        style_text = self._format_style_stats(stats)
        console.print(f"[green]  口头禅候选: {[b for b, _ in stats['ex_top_bigrams'][:5]]}[/green]")
        console.print(f"[green]  高频 emoji: {[e for e, _ in stats['ex_emojis'][:3]]}[/green]")

        # Step 2: Few-shot prompting
        console.print("[cyan]Step 2: Few-shot 人格建模...[/cyan]")
        chat_log = self._format_chat_log(messages)

        # 截断过长记录
        max_lines = self.config.get("persona", {}).get("chat_history_limit", 10) * 50
        lines = chat_log.split("\n")
        if len(lines) > max_lines:
            chat_log = "\n".join(lines[-max_lines:])
            console.print(f"[yellow]聊天记录过长，截取最后 {max_lines} 行[/yellow]")

        prompt = FEW_SHOT_PROMPT.format(chat_log=chat_log, style_stats=style_text)
        console.print("[cyan]  调用 MIMO 生成人格模型...[/cyan]")

        persona = await self._call_mimo(prompt)

        # 附加统计摘要
        persona += f"\n\n---\n\n## 📊 数据支撑（自动生成）\n\n```json\n{json.dumps(stats, ensure_ascii=False, indent=2, default=str)}\n```"

        # Header
        persona = f"""# 赛博前任人格模型 v2

> 本文件由「复活吧我的赛博前任」自动生成
> 基于 few-shot prompting + n-gram 语言风格统计
> 用于指导 AI 以 TA 的风格进行对话

---

{persona}

---

## 使用说明

1. 将本文件作为 system prompt 的一部分
2. Few-shot 示例直接作为 few-shot prompt 使用
3. 统计数据可用于验证回复风格的一致性
"""

        return persona
