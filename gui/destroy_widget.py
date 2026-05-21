#!/usr/bin/env python3
"""数据销毁页面"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt

from gui.styles import COLORS
from gui.logger import get_logger

logger = get_logger("destroy")

DESTROY_TARGETS = [
    ("data/screenshots/", "聊天截图原件"),
    ("data/chat_log.json", "提取的聊天记录"),
    ("data/chat_log_cleaned.json", "清洗后的聊天记录"),
    ("data/persona.md", "人格模型文件"),
    ("data/voice_model/", "声音克隆模型"),
    ("data/memory/", "对话记忆数据"),
    ("data/memory.json", "记忆索引"),
    ("data/imported/", "导入的原始文件"),
    ("data/logs/", "运行日志"),
    ("data/.consent.json", "伦理同意记录"),
]


class DestroyWidget(QWidget):
    """数据销毁页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self._init_ui()
        self._scan()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🔥 数据销毁")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("安全删除所有本地数据 — 文件覆写（零填充）后删除，确保不可恢复")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.scan_btn = QPushButton("🔍 重新扫描")
        self.scan_btn.setObjectName("secondary")
        self.scan_btn.clicked.connect(self._scan)
        toolbar.addWidget(self.scan_btn)

        self.select_all_btn = QPushButton("☑️ 全选")
        self.select_all_btn.setObjectName("secondary")
        self.select_all_btn.clicked.connect(self._select_all)
        toolbar.addWidget(self.select_all_btn)

        self.destroy_btn = QPushButton("🔥 销毁选中")
        self.destroy_btn.setObjectName("danger")
        self.destroy_btn.clicked.connect(self._destroy_selected)
        toolbar.addWidget(self.destroy_btn)

        self.destroy_all_btn = QPushButton("🔥🔥 销毁全部")
        self.destroy_all_btn.setObjectName("danger")
        self.destroy_all_btn.clicked.connect(self._destroy_all)
        toolbar.addWidget(self.destroy_all_btn)

        toolbar.addStretch()

        self.total_label = QLabel("")
        self.total_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        toolbar.addWidget(self.total_label)

        layout.addLayout(toolbar)

        # 数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["选择", "路径", "说明", "文件数", "大小"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # 警告
        warning = QLabel("⚠️ 数据销毁不可撤销！请确认后再操作。")
        warning.setStyleSheet(f"color: {COLORS['error']}; font-size: 14px; font-weight: bold; padding: 12px;")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)

    def _scan(self):
        """扫描本地数据"""
        self.table.setRowCount(len(DESTROY_TARGETS))
        total_size = 0
        total_files = 0

        for i, (rel_path, desc) in enumerate(DESTROY_TARGETS):
            full_path = self.base_dir / rel_path
            exists = full_path.exists()
            size = 0
            file_count = 0

            if exists:
                if full_path.is_file():
                    size = full_path.stat().st_size
                    file_count = 1
                elif full_path.is_dir():
                    for f in full_path.rglob("*"):
                        if f.is_file():
                            size += f.stat().st_size
                            file_count += 1

            total_size += size
            total_files += file_count

            # 选择框
            cb = QCheckBox()
            cb.setEnabled(exists)
            if exists:
                cb.setChecked(True)
            self.table.setCellWidget(i, 0, cb)

            self.table.setItem(i, 1, QTableWidgetItem(rel_path))
            self.table.setItem(i, 2, QTableWidgetItem(desc))

            if exists:
                self.table.setItem(i, 3, QTableWidgetItem(str(file_count)))
                self.table.setItem(i, 4, QTableWidgetItem(self._format_size(size)))
            else:
                self.table.setItem(i, 3, QTableWidgetItem("—"))
                self.table.setItem(i, 4, QTableWidgetItem("—"))

        self.total_label.setText(f"总计: {total_files} 个文件, {self._format_size(total_size)}")

    def _select_all(self):
        for i in range(self.table.rowCount()):
            cb = self.table.cellWidget(i, 0)
            if cb and cb.isEnabled():
                cb.setChecked(True)

    def _get_selected(self):
        selected = []
        for i in range(self.table.rowCount()):
            cb = self.table.cellWidget(i, 0)
            if cb and cb.isChecked():
                selected.append(DESTROY_TARGETS[i])
        return selected

    def _destroy_selected(self):
        targets = self._get_selected()
        if not targets:
            QMessageBox.information(self, "提示", "未选择任何数据")
            return

        names = "\n".join([f"• {t[1]}" for t in targets])
        reply = QMessageBox.warning(
            self, "确认销毁",
            f"即将销毁以下数据：\n\n{names}\n\n⚠️ 此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._do_destroy(targets)

    def _destroy_all(self):
        reply = QMessageBox.warning(
            self, "确认销毁全部",
            "即将销毁所有本地数据！\n\n⚠️ 此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            targets = [(t[0], t[1]) for t in DESTROY_TARGETS]
            self._do_destroy(targets)

    def _do_destroy(self, targets):
        """执行销毁"""
        import os

        for rel_path, desc in targets:
            full_path = self.base_dir / rel_path
            if not full_path.exists():
                continue

            try:
                if full_path.is_file():
                    self._secure_delete_file(full_path)
                elif full_path.is_dir():
                    for f in full_path.rglob("*"):
                        if f.is_file():
                            self._secure_delete_file(f)
                    import shutil
                    shutil.rmtree(full_path)
                logger.info(f"已销毁: {rel_path}")
            except Exception as e:
                logger.error(f"销毁失败 {rel_path}: {e}")

        QMessageBox.information(self, "完成", "✅ 数据销毁完成")
        self._scan()

    def _secure_delete_file(self, filepath: Path):
        """安全删除文件"""
        import os
        size = filepath.stat().st_size
        with open(filepath, "wb") as f:
            f.write(b"\x00" * size)
            f.flush()
            os.fsync(f.fileno())
        filepath.unlink()

    def _format_size(self, size):
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
