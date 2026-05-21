#!/usr/bin/env python3
"""
智能数据清洗 — 过滤系统消息、广告、重复内容、无效对话
"""

import re
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from rich.console import Console

console = Console()


# ─────────────────────────────────────────────
# 系统消息模式
# ─────────────────────────────────────────────
SYSTEM_PATTERNS = [
    # 微信系统消息
    r"^(你|对方|我)\s*(撤回了一条消息|sent a recall)",
    r"^\[.+\]$",
    r"^—+\s*以下为新消息\s*—+$",
    r"^——.*——$",
    r"^(你|对方|我)\s*(添加了|邀请|加入了|退出了|移除了|修改了群名)",
    r"^(你|对方|我)\s*成为(了)?群(主|管理员)",
    r"^群公告[:：]",
    r"^(你|对方|我)\s*(拍了拍|戳了戳|patted)",
    r"^\d{4}年\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2}$",  # 纯时间行
    r"^以下是新消息",
    r"^(语音|视频)通话\s*\d+:\d+$",
    r"^通话时长",
    r"^(你|对方|我)\s*分享了一个(链接|位置|文件|小程序|名片|音乐|视频号)",
    # QQ 系统消息
    r"^(.*?)\s*加入了群聊",
    r"^(.*?)\s*撤回了一条消息",
    r"^红包.*已被领取$",
    # 通用
    r"^\s*$",
    r"^\.{3,}$",
    r"^…+$",
]

# 广告/推广模式
AD_PATTERNS = [
    r"(优惠|折扣|促销|秒杀|限时|抢购|下单|包邮|加微信|加我|扫码|付款|转账)",
    r"(代购|微商|代理|加盟|兼职|日入|月入|赚钱|投资|理财|基金|股票)",
    r"(http[s]?://[^\s]+|www\.[^\s]+)",  # URL（可能是广告）
    r"(复制.*打开|点击.*链接|扫.*码|长按.*识别)",
]

# 无效内容
INVALID_PATTERNS = [
    r"^\s*$",  # 空白
    r"^[\U0001F600-\U0001F64F]+$",  # 纯表情行
    r"^[\W\s]+$",  # 纯标点/符号
]


class DataCleaner:
    """智能数据清洗器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._system_re = [re.compile(p, re.IGNORECASE) for p in SYSTEM_PATTERNS]
        self._ad_re = [re.compile(p, re.IGNORECASE) for p in AD_PATTERNS]
        self._invalid_re = [re.compile(p) for p in INVALID_PATTERNS]

    def clean(self, messages: list[dict], options: dict = None) -> list[dict]:
        """
        完整清洗流程

        options:
            remove_system: bool = True
            remove_ads: bool = True
            remove_duplicates: bool = True
            remove_invalid: bool = True
            merge_consecutive: bool = True
            fix_timestamps: bool = True
            min_text_length: int = 1
        """
        opts = {
            "remove_system": True,
            "remove_ads": True,
            "remove_duplicates": True,
            "remove_invalid": True,
            "merge_consecutive": True,
            "fix_timestamps": True,
            "min_text_length": 1,
            **(options or {}),
        }

        original_count = len(messages)
        console.print(f"[cyan]开始清洗: {original_count} 条消息[/cyan]")

        if opts["remove_system"]:
            messages = self._remove_system(messages)
            console.print(f"  系统消息过滤后: {len(messages)} 条")

        if opts["remove_ads"]:
            messages = self._remove_ads(messages)
            console.print(f"  广告过滤后: {len(messages)} 条")

        if opts["remove_invalid"]:
            messages = self._remove_invalid(messages, opts["min_text_length"])
            console.print(f"  无效内容过滤后: {len(messages)} 条")

        if opts["remove_duplicates"]:
            messages = self._dedup_advanced(messages)
            console.print(f"  去重后: {len(messages)} 条")

        if opts["fix_timestamps"]:
            messages = self._fix_timestamps(messages)

        if opts["merge_consecutive"]:
            messages = self._merge_consecutive(messages)
            console.print(f"  合并后: {len(messages)} 条")

        console.print(f"[green]✅ 清洗完成: {original_count} → {len(messages)} 条[/green]")
        return messages

    def _remove_system(self, messages: list[dict]) -> list[dict]:
        """过滤系统消息"""
        cleaned = []
        for msg in messages:
            text = msg.get("text", "").strip()
            if not text:
                continue
            if any(p.search(text) for p in self._system_re):
                continue
            # 过滤 type=system 的消息
            if msg.get("type") == "system":
                continue
            cleaned.append(msg)
        return cleaned

    def _remove_ads(self, messages: list[dict]) -> list[dict]:
        """过滤广告/推广"""
        cleaned = []
        for msg in messages:
            text = msg.get("text", "").strip()
            # 广告通常很长且包含营销关键词
            ad_score = sum(1 for p in self._ad_re if p.search(text))
            if ad_score >= 2:  # 命中2个以上广告模式
                continue
            cleaned.append(msg)
        return cleaned

    def _remove_invalid(self, messages: list[dict], min_length: int = 1) -> list[dict]:
        """过滤无效内容"""
        cleaned = []
        for msg in messages:
            text = msg.get("text", "").strip()
            if len(text) < min_length:
                continue
            if any(p.match(text) for p in self._invalid_re):
                continue
            cleaned.append(msg)
        return cleaned

    def _dedup_advanced(self, messages: list[dict]) -> list[dict]:
        """高级去重 — 基于文本相似度 + 时间窗口"""
        if not messages:
            return []

        unique = []
        seen_texts = set()

        for msg in messages:
            text = msg.get("text", "").strip()
            # 规范化后比较
            normalized = re.sub(r"\s+", " ", text).lower()

            if normalized in seen_texts:
                continue

            # 检查是否与已有消息高度相似（编辑距离）
            is_dup = False
            for seen in seen_texts:
                if self._text_similarity(normalized, seen) > 0.95:
                    is_dup = True
                    break

            if not is_dup:
                seen_texts.add(normalized)
                unique.append(msg)

        return unique

    def _text_similarity(self, a: str, b: str) -> float:
        """简单文本相似度（基于最长公共子序列比率）"""
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0

        # 长度差异过大直接判为不相似
        if abs(len(a) - len(b)) / max(len(a), len(b)) > 0.3:
            return 0.0

        # 简单字符重叠率
        set_a = set(a)
        set_b = set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def _fix_timestamps(self, messages: list[dict]) -> list[dict]:
        """修复/规范化时间戳"""
        for msg in messages:
            time_str = msg.get("time", "")
            if not time_str:
                continue

            # 尝试解析各种时间格式
            for fmt in [
                "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
                "%m-%d %H:%M", "%m/%d %H:%M",
                "%H:%M", "%Y年%m月%d日 %H:%M",
                "%Y年%m月%d日 %H:%M:%S",
            ]:
                try:
                    dt = datetime.strptime(time_str.strip(), fmt)
                    msg["time"] = dt.strftime("%Y-%m-%d %H:%M")
                    break
                except ValueError:
                    continue

        return messages

    def _merge_consecutive(self, messages: list[dict]) -> list[dict]:
        """合并连续同一角色的短消息（5分钟内）"""
        if not messages:
            return []

        merged = [messages[0].copy()]

        for msg in messages[1:]:
            prev = merged[-1]
            same_role = msg.get("role") == prev.get("role")

            # 检查时间窗口
            time_close = True
            if msg.get("time") and prev.get("time"):
                try:
                    t1 = datetime.strptime(prev["time"], "%Y-%m-%d %H:%M")
                    t2 = datetime.strptime(msg["time"], "%Y-%m-%d %H:%M")
                    time_close = abs((t2 - t1).total_seconds()) < 300  # 5分钟
                except ValueError:
                    pass

            if same_role and time_close:
                prev["text"] = prev.get("text", "") + "\n" + msg.get("text", "")
            else:
                merged.append(msg.copy())

        return merged


def clean_chat_file(input_path: Path, output_path: Path, config: dict = None, options: dict = None):
    """清洗聊天记录文件"""
    with open(input_path, "r", encoding="utf-8") as f:
        messages = json.load(f)

    cleaner = DataCleaner(config)
    cleaned = cleaner.clean(messages, options)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    console.print(f"[green]✅ 已保存清洗结果 → {output_path}[/green]")
    return cleaned
