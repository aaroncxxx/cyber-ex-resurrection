#!/usr/bin/env python3
"""
伦理声明 & 同意验证 — 强制执行
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()

ETHICS_DECLARATION = """
╔══════════════════════════════════════════════════════════════╗
║                   ⚖️  伦理与法律声明                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  本工具仅供以下合法用途：                                      ║
║  ✅ 纪念已故亲人（需获得家属同意）                               ║
║  ✅ 本人授权的个人聊天记录备份与分析                             ║
║  ✅ 已获明确书面同意的学术研究                                  ║
║  ✅ 创意虚构角色（非真实人物）                                  ║
║                                                              ║
║  严禁以下用途：                                                ║
║  🚫 未经授权克隆他人人格                                       ║
║  🚫 冒充他人进行欺诈、骚扰或诈骗                                ║
║  🚫 制作深度伪造内容（Deepfake）                               ║
║  🚫 侵犯他人隐私权、肖像权、名誉权                              ║
║  🚫 用于任何形式的网络霸凌或精神控制                             ║
║  🚫 违反所在地区法律法规的任何行为                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

LEGAL_REFERENCES = """
📖 相关法律条文参考：

【中国】
• 《民法典》第1019条 — 任何组织或个人不得利用信息技术手段伪造等方式侵害他人的肖像权
• 《民法典》第1034条 — 自然人的个人信息受法律保护
• 《民法典》第1024条 — 民事主体享有名誉权，任何组织或个人不得以侮辱、诽谤等方式侵害
• 《个人信息保护法》第14条 — 处理个人信息应取得个人同意
• 《网络安全法》第44条 — 禁止非法获取、出售、提供个人信息
• 《刑法》第253条之一 — 侵犯公民个人信息罪

【欧盟】
• GDPR 第22条 — 自动化个人决策，包括画像
• GDPR 第17条 — 被遗忘权（数据删除权）

【美国】
• CCPA — 加州消费者隐私法案
• 各州 Deepfake 法案

⚖️ 违反上述法律可能导致民事赔偿、行政处罚甚至刑事责任。
"""

CONSENT_PROMPT = """
┌──────────────────────────────────────────────────────┐
│  📋 使用前承诺（必须逐项确认）                          │
└──────────────────────────────────────────────────────┘
"""


class EthicsChecker:
    """伦理合规检查器"""

    CONSENT_FILE = "data/.consent.json"

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.consent_path = base_dir / self.CONSENT_FILE

    def show_declaration(self):
        """展示伦理声明"""
        console.print(Panel(ETHICS_DECLARATION, border_style="red", title="⚠️ 伦理声明"))

    def show_legal_references(self):
        """展示法律参考"""
        console.print(Panel(LEGAL_REFERENCES, border_style="yellow", title="📖 法律风险提示"))

    def require_consent(self) -> bool:
        """要求用户逐项确认同意，返回是否全部通过"""
        self.show_declaration()
        console.print(CONSENT_PROMPT)

        questions = [
            ("consent_auth", "我确认已获得被克隆人的明确书面同意，或被克隆人已故且获得家属同意"),
            ("purpose_limit", "我承诺仅将本工具用于合法、正当、必要的目的"),
            ("no_harm", "我承诺不使用本工具进行欺诈、骚扰、诽谤或任何形式的伤害"),
            ("legal_aware", "我已阅读并理解相关法律法规，知晓违法行为的法律后果"),
            ("data_responsibility", "我承诺妥善保管生成的数据，不向第三方泄露"),
        ]

        for key, text in questions:
            console.print(f"\n  [cyan]• {text}[/cyan]")
            if not Confirm.ask("    确认", default=False):
                console.print(f"[red]❌ 未确认以上条款，无法使用本工具。[/red]")
                return False

        # 保存同意记录
        consent_record = {
            "timestamp": time.time(),
            "timestamp_human": time.strftime("%Y-%m-%d %H:%M:%S"),
            "consent_hash": self._hash_consent(),
            "version": "1.1.1",
        }
        self.consent_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.consent_path, "w", encoding="utf-8") as f:
            json.dump(consent_record, f, ensure_ascii=False, indent=2)

        console.print("[green]✅ 伦理确认完成，记录已保存。[/green]")
        return True

    def check_consent(self) -> bool:
        """检查是否已通过伦理确认"""
        if not self.consent_path.exists():
            return False

        try:
            with open(self.consent_path, "r", encoding="utf-8") as f:
                record = json.load(f)
            return record.get("consent_hash") == self._hash_consent()
        except Exception:
            return False

    def ensure_consent(self) -> bool:
        """确保已通过伦理确认，否则要求确认"""
        if self.check_consent():
            return True
        return self.require_consent()

    def revoke_consent(self):
        """撤销同意记录"""
        if self.consent_path.exists():
            self.consent_path.unlink()
            console.print("[yellow]⚠️ 同意记录已撤销。[/yellow]")

    def _hash_consent(self) -> str:
        """生成同意内容哈希，用于检测声明变更"""
        content = "|".join([
            "consent_auth", "purpose_limit", "no_harm",
            "legal_aware", "data_responsibility", "v1.2.0"
        ])
        return hashlib.sha256(content.encode()).hexdigest()[:16]
