#!/usr/bin/env python3
"""伦理声明页面"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTextEdit, QCheckBox, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from gui.styles import COLORS
from gui.logger import get_logger

logger = get_logger("consent")


class ConsentWidget(QWidget):
    """伦理声明 & 同意确认"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self._init_ui()
        self._check_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title = QLabel("⚖️ 伦理与法律声明")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("首次使用前必须完成伦理确认，这是法律要求")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 伦理声明内容
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(300)

        content = QLabel()
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setText("""
        <div style="line-height: 1.8; padding: 12px;">
        <h3 style="color: #e94560;">🚫 严禁以下用途：</h3>
        <ul>
        <li>未经授权克隆他人人格</li>
        <li>冒充他人进行欺诈、骚扰或诈骗</li>
        <li>制作深度伪造内容（Deepfake）</li>
        <li>侵犯他人隐私权、肖像权、名誉权</li>
        <li>用于任何形式的网络霸凌或精神控制</li>
        </ul>

        <h3 style="color: #2ed573;">✅ 仅限以下合法用途：</h3>
        <ul>
        <li>纪念已故亲人（需获得家属同意）</li>
        <li>本人授权的个人聊天记录备份与分析</li>
        <li>已获明确书面同意的学术研究</li>
        <li>创意虚构角色（非真实人物）</li>
        </ul>

        <h3 style="color: #ffa502;">📖 相关法律条文：</h3>
        <ul>
        <li><b>《民法典》第1019条</b> — 禁止伪造侵害肖像权</li>
        <li><b>《民法典》第1034条</b> — 个人信息保护</li>
        <li><b>《个人信息保护法》第14条</b> — 处理个人信息需同意</li>
        <li><b>《刑法》第253条之一</b> — 侵犯公民个人信息罪</li>
        <li><b>GDPR 第17条</b> — 被遗忘权（数据删除权）</li>
        </ul>

        <p style="color: #ff4757;"><b>⚠️ 违反上述法律可能导致民事赔偿、行政处罚甚至刑事责任。</b></p>
        </div>
        """)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # 确认复选框
        self.checkboxes = []
        checks_frame = QFrame()
        checks_frame.setObjectName("card")
        checks_layout = QVBoxLayout(checks_frame)

        check_items = [
            "我确认已获得被克隆人的明确书面同意，或被克隆人已故且获得家属同意",
            "我承诺仅将本工具用于合法、正当、必要的目的",
            "我承诺不使用本工具进行欺诈、骚扰、诽谤或任何形式的伤害",
            "我已阅读并理解相关法律法规，知晓违法行为的法律后果",
            "我承诺妥善保管生成的数据，不向第三方泄露",
        ]

        for text in check_items:
            cb = QCheckBox(text)
            cb.setStyleSheet(f"color: {COLORS['text']}; padding: 4px;")
            cb.stateChanged.connect(self._update_confirm_btn)
            checks_layout.addWidget(cb)
            self.checkboxes.append(cb)

        layout.addWidget(checks_frame)

        # 按钮行
        btn_layout = QHBoxLayout()

        self.confirm_btn = QPushButton("✅ 确认并继续")
        self.confirm_btn.setObjectName("primary")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setFixedHeight(44)
        self.confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(self.confirm_btn)

        self.revoke_btn = QPushButton("❌ 撤销同意")
        self.revoke_btn.setObjectName("danger")
        self.revoke_btn.setFixedHeight(44)
        self.revoke_btn.clicked.connect(self._revoke)
        btn_layout.addWidget(self.revoke_btn)

        btn_layout.addStretch()

        # 状态
        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        btn_layout.addWidget(self.status_label)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _update_confirm_btn(self):
        """检查是否所有复选框都已勾选"""
        all_checked = all(cb.isChecked() for cb in self.checkboxes)
        self.confirm_btn.setEnabled(all_checked)

    def _check_status(self):
        """检查当前伦理确认状态"""
        consent_file = self.base_dir / "data" / ".consent.json"
        if consent_file.exists():
            self.status_label.setText("✅ 已通过伦理确认")
            self.status_label.setStyleSheet(f"color: {COLORS['success']};")
        else:
            self.status_label.setText("❌ 尚未确认")
            self.status_label.setStyleSheet(f"color: {COLORS['error']};")

    def _confirm(self):
        """确认同意"""
        import json, time
        import hashlib

        consent_data = {
            "timestamp": time.time(),
            "timestamp_human": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.1.1",
            "items_confirmed": len(self.checkboxes),
        }

        consent_file = self.base_dir / "data" / ".consent.json"
        consent_file.parent.mkdir(parents=True, exist_ok=True)

        with open(consent_file, "w", encoding="utf-8") as f:
            json.dump(consent_data, f, ensure_ascii=False, indent=2)

        logger.info("伦理确认完成")
        self._check_status()

        QMessageBox.information(self, "确认成功", "✅ 伦理确认已完成。\n现在可以使用本工具的全部功能。")

    def _revoke(self):
        """撤销同意"""
        reply = QMessageBox.warning(
            self, "撤销确认",
            "确定要撤销伦理同意吗？\n撤销后将无法使用本工具的功能。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            consent_file = self.base_dir / "data" / ".consent.json"
            if consent_file.exists():
                consent_file.unlink()
            logger.info("伦理同意已撤销")
            self._check_status()
