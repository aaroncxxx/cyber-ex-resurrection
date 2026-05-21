#!/usr/bin/env python3
"""数据清洗页面"""

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QCheckBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from gui.styles import COLORS
from gui.logger import get_logger

logger = get_logger("clean")


class CleanWorker(QThread):
    """清洗工作线程"""
    finished = pyqtSignal(list, dict)  # (cleaned, stats)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, base_dir, messages, options):
        super().__init__()
        self.base_dir = base_dir
        self.messages = messages
        self.options = options

    def run(self):
        try:
            import sys
            sys.path.insert(0, str(self.base_dir))
            from data_cleaner import DataCleaner

            cleaner = DataCleaner()
            original = len(self.messages)

            # 逐步清洗并记录
            messages = self.messages
            stats = {"original": original}

            if self.options.get("remove_system"):
                before = len(messages)
                messages = [m for m in messages if m.get("type") != "system"]
                # 简化的系统消息过滤
                import re
                system_re = [re.compile(p) for p in [
                    r"撤回了一条消息", r"^添加了", r"^邀请", r"加入了群聊",
                    r"^——.*——$", r"拍了拍", r"^\.{3,}$"
                ]]
                cleaned = []
                for m in messages:
                    text = m.get("text", "").strip()
                    if any(p.search(text) for p in system_re):
                        continue
                    cleaned.append(m)
                messages = cleaned
                stats["system_removed"] = before - len(messages)
                self.log.emit(f"系统消息过滤: {before} → {len(messages)}")

            if self.options.get("remove_duplicates"):
                before = len(messages)
                seen = set()
                unique = []
                for m in messages:
                    key = (m.get("role", ""), m.get("text", ""))
                    if key not in seen:
                        seen.add(key)
                        unique.append(m)
                messages = unique
                stats["duplicates_removed"] = before - len(messages)
                self.log.emit(f"去重: {before} → {len(messages)}")

            if self.options.get("remove_invalid"):
                before = len(messages)
                messages = [m for m in messages if m.get("text", "").strip() and len(m.get("text", "").strip()) > 1]
                stats["invalid_removed"] = before - len(messages)
                self.log.emit(f"无效内容过滤: {before} → {len(messages)}")

            stats["final"] = len(messages)
            self.finished.emit(messages, stats)
        except Exception as e:
            self.error.emit(str(e))


class CleanWidget(QWidget):
    """数据清洗页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.messages = []
        self.cleaned = []
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🧹 智能数据清洗")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("过滤系统消息、广告、重复内容和无效对话")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.load_btn = QPushButton("📂 加载聊天记录")
        self.load_btn.setObjectName("secondary")
        self.load_btn.clicked.connect(self._load)
        toolbar.addWidget(self.load_btn)

        self.clean_btn = QPushButton("🧹 开始清洗")
        self.clean_btn.setObjectName("primary")
        self.clean_btn.clicked.connect(self._clean)
        self.clean_btn.setEnabled(False)
        toolbar.addWidget(self.clean_btn)

        self.save_btn = QPushButton("💾 保存结果")
        self.save_btn.setObjectName("secondary")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(False)
        toolbar.addWidget(self.save_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 清洗选项
        opts_frame = QFrame()
        opts_frame.setObjectName("card")
        opts_layout = QHBoxLayout(opts_frame)

        self.opt_system = QCheckBox("过滤系统消息")
        self.opt_system.setChecked(True)
        opts_layout.addWidget(self.opt_system)

        self.opt_ads = QCheckBox("过滤广告")
        self.opt_ads.setChecked(True)
        opts_layout.addWidget(self.opt_ads)

        self.opt_dedup = QCheckBox("去重")
        self.opt_dedup.setChecked(True)
        opts_layout.addWidget(self.opt_dedup)

        self.opt_invalid = QCheckBox("过滤无效内容")
        self.opt_invalid.setChecked(True)
        opts_layout.addWidget(self.opt_invalid)

        self.opt_merge = QCheckBox("合并连续消息")
        self.opt_merge.setChecked(True)
        opts_layout.addWidget(self.opt_merge)

        opts_layout.addStretch()
        layout.addWidget(opts_frame)

        # 预览
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["角色", "消息", "状态"])
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.preview_table)

        # 统计
        stats_layout = QHBoxLayout()
        self.stats_before = QLabel("清洗前: —")
        self.stats_before.setStyleSheet(f"color: {COLORS['text_dim']};")
        stats_layout.addWidget(self.stats_before)

        self.stats_after = QLabel("清洗后: —")
        self.stats_after.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        stats_layout.addWidget(self.stats_after)

        stats_layout.addStretch()

        self.stats_removed = QLabel("已过滤: —")
        self.stats_removed.setStyleSheet(f"color: {COLORS['warning']};")
        stats_layout.addWidget(self.stats_removed)

        layout.addLayout(stats_layout)

        # 日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet(f"background-color: {COLORS['input_bg']};")
        layout.addWidget(self.log_text)

    def _load(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "加载聊天记录", "data/", "JSON (*.json)"
        )
        if file:
            with open(file, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
            self.clean_btn.setEnabled(True)
            self.stats_before.setText(f"清洗前: {len(self.messages)} 条")
            self.log_text.append(f"加载 {len(self.messages)} 条消息")

    def _clean(self):
        if not self.messages:
            return

        options = {
            "remove_system": self.opt_system.isChecked(),
            "remove_ads": self.opt_ads.isChecked(),
            "remove_duplicates": self.opt_dedup.isChecked(),
            "remove_invalid": self.opt_invalid.isChecked(),
        }

        self.clean_btn.setEnabled(False)
        self.worker = CleanWorker(self.base_dir, self.messages, options)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.log.connect(lambda m: self.log_text.append(m))
        self.worker.start()

    def _on_finished(self, cleaned, stats):
        self.cleaned = cleaned
        self.clean_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

        self.stats_after.setText(f"清洗后: {len(cleaned)} 条")
        removed = stats.get("original", 0) - len(cleaned)
        self.stats_removed.setText(f"已过滤: {removed} 条")

        # 预览
        self.preview_table.setRowCount(min(len(cleaned), 200))
        for i, msg in enumerate(cleaned[:200]):
            role = "我" if msg.get("role") == "me" else "TA"
            self.preview_table.setItem(i, 0, QTableWidgetItem(role))
            self.preview_table.setItem(i, 1, QTableWidgetItem(msg.get("text", "")[:120]))
            self.preview_table.setItem(i, 2, QTableWidgetItem("✅"))

        logger.info(f"清洗完成: {stats.get('original', 0)} → {len(cleaned)}")

    def _on_error(self, error):
        self.clean_btn.setEnabled(True)
        self.log_text.append(f"❌ {error}")

    def _save(self):
        if not self.cleaned:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存", "data/chat_log_cleaned.json", "JSON (*.json)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.cleaned, f, ensure_ascii=False, indent=2)
            self.log_text.append(f"💾 已保存: {path}")
