#!/usr/bin/env python3
"""人格预览页面 — 可视化人格模型"""

import json
import asyncio
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QTextEdit, QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from gui.styles import COLORS
from gui.logger import get_logger

logger = get_logger("persona")


class PersonaWorker(QThread):
    """人格构建工作线程"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, base_dir, chat_file):
        super().__init__()
        self.base_dir = base_dir
        self.chat_file = chat_file

    def run(self):
        try:
            import sys
            sys.path.insert(0, str(self.base_dir))
            from persona_builder import PersonaBuilder

            config_path = self.base_dir / "config.json"
            with open(config_path, "r") as f:
                config = json.load(f)

            builder = PersonaBuilder(config)
            persona_text = asyncio.run(builder.build(Path(self.chat_file)))
            self.finished.emit(persona_text)
        except Exception as e:
            self.error.emit(str(e))


class PersonaWidget(QWidget):
    """人格预览页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.persona_text = ""
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🧠 人格预览")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("从聊天记录中提取语言风格、口头禅、性格特征，实时预览效果")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.load_btn = QPushButton("📂 加载聊天记录")
        self.load_btn.setObjectName("secondary")
        self.load_btn.clicked.connect(self._load_chat)
        toolbar.addWidget(self.load_btn)

        self.build_btn = QPushButton("🧠 生成人格模型")
        self.build_btn.setObjectName("primary")
        self.build_btn.clicked.connect(self._build_persona)
        self.build_btn.setEnabled(False)
        toolbar.addWidget(self.build_btn)

        self.save_btn = QPushButton("💾 保存人格")
        self.save_btn.setObjectName("secondary")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(False)
        toolbar.addWidget(self.save_btn)

        toolbar.addStretch()

        self.status_label = QLabel("未开始")
        self.status_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        toolbar.addWidget(self.status_label)

        layout.addLayout(toolbar)

        # 进度
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # 主内容 — 左右分栏
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：聊天记录预览
        left = QFrame()
        left.setObjectName("card")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("💬 聊天记录样本"))
        self.chat_preview = QTextEdit()
        self.chat_preview.setReadOnly(True)
        self.chat_preview.setFont(QFont("Consolas", 11))
        self.chat_preview.setPlaceholderText("加载聊天记录后在此预览...")
        left_layout.addWidget(self.chat_preview)
        splitter.addWidget(left)

        # 右侧：人格输出
        right = QFrame()
        right.setObjectName("card")
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("🎭 人格模型"))
        self.persona_output = QTextEdit()
        self.persona_output.setReadOnly(True)
        self.persona_output.setFont(QFont("Microsoft YaHei", 12))
        self.persona_output.setPlaceholderText("生成人格模型后在此预览...\n\n包含：\n• 语言风格分析\n• 口头禅提取\n• 性格特征\n• 回复示例")
        right_layout.addWidget(self.persona_output)
        splitter.addWidget(right)

        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

        # 统计
        stats_layout = QHBoxLayout()
        self.msg_count = QLabel("消息数: —")
        self.msg_count.setStyleSheet(f"color: {COLORS['text_dim']};")
        stats_layout.addWidget(self.msg_count)

        self.persona_size = QLabel("人格大小: —")
        self.persona_size.setStyleSheet(f"color: {COLORS['text_dim']};")
        stats_layout.addWidget(self.persona_size)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

    def _load_chat(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "加载聊天记录", "data/", "JSON (*.json)"
        )
        if file:
            with open(file, "r", encoding="utf-8") as f:
                messages = json.load(f)

            # 预览聊天记录
            lines = []
            for msg in messages[:100]:
                role = "我" if msg.get("role") == "me" else "TA"
                lines.append(f"[{role}] {msg.get('text', '')}")
            self.chat_preview.setPlainText("\n".join(lines))
            self.msg_count.setText(f"消息数: {len(messages)}")

            self.chat_file = file
            self.build_btn.setEnabled(True)
            self.status_label.setText("已加载")

    def _build_persona(self):
        if not hasattr(self, 'chat_file'):
            return

        self.build_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("生成中...")
        self.persona_output.clear()

        self.worker = PersonaWorker(self.base_dir, self.chat_file)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, persona_text):
        self.persona_text = persona_text
        self.persona_output.setPlainText(persona_text)
        self.build_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText("✅ 生成完成")
        self.persona_size.setText(f"人格大小: {len(persona_text)} 字符")
        logger.info(f"人格生成完成: {len(persona_text)} 字符")

    def _on_error(self, error):
        self.build_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText(f"❌ {error}")
        logger.error(f"人格生成失败: {error}")

    def _save(self):
        if not self.persona_text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存人格", "data/persona.md", "Markdown (*.md)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.persona_text)
            self.status_label.setText(f"💾 已保存: {path}")
