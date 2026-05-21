#!/usr/bin/env python3
"""仪表盘 — 项目总览"""

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QPushButton, QProgressBar, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from gui.styles import COLORS


class StatCard(QFrame):
    """统计卡片"""

    def __init__(self, icon, label, value="0", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 20))
        header.addWidget(icon_label)
        header.addStretch()
        layout.addLayout(header)

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("stat_value")
        layout.addWidget(self.value_label)

        label_widget = QLabel(label)
        label_widget.setObjectName("stat_label")
        layout.addWidget(label_widget)

    def update_value(self, value):
        self.value_label.setText(str(value))


class DashboardWidget(QWidget):
    """仪表盘页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self._init_ui()
        self._refresh_data()

        # 自动刷新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_data)
        self.timer.start(5000)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 标题
        title = QLabel("📊 仪表盘")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("项目总览 — 实时监控数据状态")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        # 统计卡片行
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_screenshots = StatCard("📸", "截图文件", "0")
        self.card_messages = StatCard("💬", "聊天消息", "0")
        self.card_persona = StatCard("🧠", "人格状态", "未生成")
        self.card_voice = StatCard("🎤", "声音模型", "未训练")
        self.card_ethics = StatCard("⚖️", "伦理确认", "未确认")

        for card in [self.card_screenshots, self.card_messages,
                     self.card_persona, self.card_voice, self.card_ethics]:
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)

        # 快速操作区
        actions_frame = QFrame()
        actions_frame.setObjectName("card")
        actions_layout = QVBoxLayout(actions_frame)

        actions_title = QLabel("⚡ 快速操作")
        actions_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['accent']};")
        actions_layout.addWidget(actions_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        quick_buttons = [
            ("📸 截图识别", "从截图提取对话"),
            ("📥 导入记录", "导入已有聊天文件"),
            ("🧹 清洗数据", "过滤无效内容"),
            ("🧠 生成人格", "构建语言模型"),
            ("🎤 克隆声音", "训练声音模型"),
            ("🚀 一键部署", "自动完成全部流程"),
        ]

        for text, tip in quick_buttons:
            btn = QPushButton(text)
            btn.setObjectName("secondary")
            btn.setToolTip(tip)
            btn.setFixedHeight(40)
            btn_row.addWidget(btn)

        actions_layout.addLayout(btn_row)
        layout.addWidget(actions_frame)

        # Pipeline 进度
        pipeline_frame = QFrame()
        pipeline_frame.setObjectName("card")
        pipeline_layout = QVBoxLayout(pipeline_frame)

        pipeline_title = QLabel("🔄 Pipeline 状态")
        pipeline_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['accent']};")
        pipeline_layout.addWidget(pipeline_title)

        self.pipeline_progress = QProgressBar()
        self.pipeline_progress.setRange(0, 100)
        self.pipeline_progress.setValue(0)
        self.pipeline_progress.setFormat("就绪 — 等待开始")
        pipeline_layout.addWidget(self.pipeline_progress)

        self.pipeline_status = QLabel("尚未运行 Pipeline")
        self.pipeline_status.setObjectName("subtitle")
        pipeline_layout.addWidget(self.pipeline_status)

        layout.addWidget(pipeline_frame)

        # 最近日志
        log_frame = QFrame()
        log_frame.setObjectName("card")
        log_layout = QVBoxLayout(log_frame)

        log_title = QLabel("📋 最近活动")
        log_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['accent']};")
        log_layout.addWidget(log_title)

        self.recent_log = QLabel("暂无活动记录")
        self.recent_log.setObjectName("subtitle")
        self.recent_log.setWordWrap(True)
        log_layout.addWidget(self.recent_log)

        layout.addWidget(log_frame)
        layout.addStretch()

    def _refresh_data(self):
        """刷新数据统计"""
        data_dir = self.base_dir / "data"

        # 截图数量
        screenshots_dir = data_dir / "screenshots"
        if screenshots_dir.exists():
            count = len(list(screenshots_dir.glob("*")))
            self.card_screenshots.update_value(count)
        else:
            self.card_screenshots.update_value("0")

        # 消息数量
        chat_log = data_dir / "chat_log.json"
        if chat_log.exists():
            try:
                with open(chat_log, "r", encoding="utf-8") as f:
                    messages = json.load(f)
                self.card_messages.update_value(len(messages))
            except Exception:
                pass

        # 人格状态
        persona_file = data_dir / "persona.md"
        if persona_file.exists():
            size = persona_file.stat().st_size
            self.card_persona.update_value(f"已生成 ({size // 1024}KB)")
        else:
            self.card_persona.update_value("未生成")

        # 声音模型
        voice_dir = data_dir / "voice_model"
        if voice_dir.exists() and any(voice_dir.iterdir()):
            self.card_voice.update_value("已训练")
        else:
            self.card_voice.update_value("未训练")

        # 伦理确认
        consent_file = data_dir / ".consent.json"
        if consent_file.exists():
            self.card_ethics.update_value("✅ 已确认")
        else:
            self.card_ethics.update_value("❌ 未确认")
