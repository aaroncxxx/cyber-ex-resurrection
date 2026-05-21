#!/usr/bin/env python3
"""导入聊天记录页面"""

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QTextEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from gui.styles import COLORS
from gui.logger import get_logger

logger = get_logger("import")


class ImportWorker(QThread):
    """导入工作线程"""
    finished = pyqtSignal(list, str)  # (messages, format)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, base_dir, file_path, fmt=None):
        super().__init__()
        self.base_dir = base_dir
        self.file_path = file_path
        self.fmt = fmt

    def run(self):
        try:
            import sys
            sys.path.insert(0, str(self.base_dir))
            from importers import ChatImporter

            path = Path(self.file_path)
            if path.is_dir():
                self.log.emit(f"扫描目录: {path}")
                messages = ChatImporter.import_directory(path)
            else:
                self.log.emit(f"导入文件: {path.name}")
                messages = ChatImporter.import_file(path, format=self.fmt)

            fmt = self.fmt or ChatImporter.detect_format(path)
            self.finished.emit(messages, fmt)
        except Exception as e:
            self.error.emit(str(e))


class ImportWidget(QWidget):
    """导入聊天记录页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.messages = []
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📥 导入聊天记录")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("支持 txt / csv / html / 微信导出 / 手机备份等格式")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.file_btn = QPushButton("📁 选择文件")
        self.file_btn.setObjectName("secondary")
        self.file_btn.clicked.connect(self._select_file)
        toolbar.addWidget(self.file_btn)

        self.dir_btn = QPushButton("📂 选择目录")
        self.dir_btn.setObjectName("secondary")
        self.dir_btn.clicked.connect(self._select_dir)
        toolbar.addWidget(self.dir_btn)

        toolbar.addWidget(QLabel("格式:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["自动检测", "json", "csv", "html", "wechat_export", "txt_timestamped", "txt_plain", "backup"])
        self.fmt_combo.setFixedWidth(140)
        toolbar.addWidget(self.fmt_combo)

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(False)
        toolbar.addWidget(self.save_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 文件路径显示
        self.path_label = QLabel("未选择文件")
        self.path_label.setStyleSheet(f"color: {COLORS['text_dim']}; padding: 8px;")
        layout.addWidget(self.path_label)

        # 预览表格
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["角色", "消息", "时间", "来源"])
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.preview_table.setAlternatingRowColors(True)
        layout.addWidget(self.preview_table)

        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.count_label = QLabel("0 条消息")
        self.count_label.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        status_layout.addWidget(self.count_label)
        layout.addLayout(status_layout)

        # 日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet(f"background-color: {COLORS['input_bg']};")
        layout.addWidget(self.log_text)

    def _select_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "选择聊天记录文件", "",
            "所有支持格式 (*.json *.csv *.html *.htm *.txt *.bak *.db);;所有文件 (*)"
        )
        if file:
            self._do_import(file)

    def _select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择聊天记录目录")
        if dir_path:
            self._do_import(dir_path)

    def _do_import(self, path):
        fmt = self.fmt_combo.currentText()
        if fmt == "自动检测":
            fmt = None

        self.path_label.setText(f"📁 {path}")
        self.log_text.clear()
        self.status_label.setText("导入中...")

        self.worker = ImportWorker(self.base_dir, path, fmt)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.log.connect(self._on_log)
        self.worker.start()

    def _on_finished(self, messages, fmt):
        self.messages = messages
        self.count_label.setText(f"{len(messages)} 条消息")
        self.status_label.setText(f"✅ 格式: {fmt}")
        self.save_btn.setEnabled(True)

        # 填充预览表格
        self.preview_table.setRowCount(min(len(messages), 200))
        for i, msg in enumerate(messages[:200]):
            role = "我" if msg.get("role") == "me" else "TA"
            self.preview_table.setItem(i, 0, QTableWidgetItem(role))
            self.preview_table.setItem(i, 1, QTableWidgetItem(msg.get("text", "")[:100]))
            self.preview_table.setItem(i, 2, QTableWidgetItem(msg.get("time", "")))
            self.preview_table.setItem(i, 3, QTableWidgetItem(msg.get("source", "")))

        logger.info(f"导入完成: {len(messages)} 条消息, 格式: {fmt}")

    def _on_error(self, error):
        self.status_label.setText(f"❌ {error}")
        logger.error(f"导入失败: {error}")

    def _on_log(self, msg):
        self.log_text.append(msg)

    def _save(self):
        if not self.messages:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存", "data/chat_log.json", "JSON (*.json)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
            self._on_log(f"💾 已保存: {path}")
