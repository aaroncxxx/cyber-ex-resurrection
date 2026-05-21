#!/usr/bin/env python3
"""运行日志页面"""

from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTextEdit, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from gui.styles import COLORS
from gui.logger import log_signal


class LogWidget(QWidget):
    """运行日志页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.all_logs = []
        self._init_ui()

        # 连接日志信号
        log_signal.log_added.connect(self._on_log)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📋 运行日志")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("实时查看系统运行状态和错误信息")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.auto_scroll = QCheckBox("自动滚动")
        self.auto_scroll.setChecked(True)
        toolbar.addWidget(self.auto_scroll)

        toolbar.addWidget(QLabel("级别:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["全部", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_filter.currentTextChanged.connect(self._filter_logs)
        toolbar.addWidget(self.level_filter)

        self.clear_btn = QPushButton("🗑 清空")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self.clear_btn)

        self.export_btn = QPushButton("💾 导出日志")
        self.export_btn.setObjectName("secondary")
        self.export_btn.clicked.connect(self._export)
        toolbar.addWidget(self.export_btn)

        toolbar.addStretch()

        self.count_label = QLabel("0 条日志")
        self.count_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        toolbar.addWidget(self.count_label)

        layout.addLayout(toolbar)

        # 日志文本
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 11))
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['input_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.log_text)

        # 加载历史日志
        self._load_history()

    def _on_log(self, level, message):
        """接收新日志"""
        self.all_logs.append((level, message))

        # 颜色映射
        color_map = {
            "DEBUG": COLORS['text_dim'],
            "INFO": COLORS['text'],
            "WARNING": COLORS['warning'],
            "ERROR": COLORS['error'],
            "CRITICAL": COLORS['error'],
        }
        color = color_map.get(level, COLORS['text'])

        # 级别过滤
        current_filter = self.level_filter.currentText()
        if current_filter != "全部" and level != current_filter:
            return

        self.log_text.append(f'<span style="color:{color}">[{level}] {message}</span>')
        self.count_label.setText(f"{len(self.all_logs)} 条日志")

        if self.auto_scroll.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _filter_logs(self, filter_text):
        """按级别过滤"""
        self.log_text.clear()
        for level, message in self.all_logs:
            if filter_text == "全部" or level == filter_text:
                color_map = {
                    "DEBUG": COLORS['text_dim'],
                    "INFO": COLORS['text'],
                    "WARNING": COLORS['warning'],
                    "ERROR": COLORS['error'],
                }
                color = color_map.get(level, COLORS['text'])
                self.log_text.append(f'<span style="color:{color}">[{level}] {message}</span>')

    def _clear(self):
        self.log_text.clear()
        self.all_logs.clear()
        self.count_label.setText("0 条日志")

    def _export(self):
        """导出日志"""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                for level, message in self.all_logs:
                    f.write(f"[{level}] {message}\n")

    def _load_history(self):
        """加载历史日志文件"""
        log_dir = self.base_dir / "data" / "logs"
        if log_dir.exists():
            gui_log = log_dir / "gui.log"
            if gui_log.exists():
                try:
                    with open(gui_log, "r", encoding="utf-8") as f:
                        lines = f.readlines()[-100:]  # 最近100行
                    for line in lines:
                        self.log_text.append(line.strip())
                except Exception:
                    pass
