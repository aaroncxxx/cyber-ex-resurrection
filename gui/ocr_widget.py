#!/usr/bin/env python3
"""截图 OCR 识别页面 — 多引擎 + 预览"""

import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QFileDialog, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QSplitter, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont

from gui.styles import COLORS
from gui.logger import get_logger

logger = get_logger("ocr")


class OCRWorker(QThread):
    """OCR 后台工作线程"""
    progress = pyqtSignal(int, int)  # (current, total)
    finished = pyqtSignal(list)      # results
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, base_dir, image_paths, engine):
        super().__init__()
        self.base_dir = base_dir
        self.image_paths = image_paths
        self.engine = engine

    def run(self):
        try:
            import sys
            sys.path.insert(0, str(self.base_dir))

            if self.engine == "multi":
                from ocr_engines import MultiEngineOCR
                import json
                config_path = self.base_dir / "config.json"
                with open(config_path, "r") as f:
                    config = json.load(f)
                ocr = MultiEngineOCR(config, ["paddleocr", "easyocr", "mimo_omni"])
            else:
                from ocr_engines import MultiEngineOCR
                import json
                config_path = self.base_dir / "config.json"
                with open(config_path, "r") as f:
                    config = json.load(f)
                ocr = MultiEngineOCR(config, [self.engine])

            all_results = []
            for i, img_path in enumerate(self.image_paths):
                self.log.emit(f"处理: {img_path.name}")
                try:
                    results = ocr.recognize(img_path)
                    for r in results:
                        r["source"] = img_path.name
                    all_results.extend(results)
                    self.log.emit(f"  ✓ {len(results)} 条消息")
                except Exception as e:
                    self.log.emit(f"  ✗ 失败: {e}")
                self.progress.emit(i + 1, len(self.image_paths))

            self.finished.emit(all_results)
        except Exception as e:
            self.error.emit(str(e))


class OCRWidget(QWidget):
    """截图 OCR 页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.image_paths = []
        self.results = []
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title = QLabel("📸 截图 OCR 识别")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("从聊天截图中提取对话内容，支持多引擎识别")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.select_btn = QPushButton("📁 选择截图目录")
        self.select_btn.setObjectName("secondary")
        self.select_btn.clicked.connect(self._select_dir)
        toolbar.addWidget(self.select_btn)

        self.add_btn = QPushButton("➕ 添加文件")
        self.add_btn.setObjectName("secondary")
        self.add_btn.clicked.connect(self._add_files)
        toolbar.addWidget(self.add_btn)

        toolbar.addWidget(QLabel("引擎:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["mimo_omni", "paddleocr", "easyocr", "multi"])
        self.engine_combo.setFixedWidth(140)
        toolbar.addWidget(self.engine_combo)

        self.start_btn = QPushButton("🚀 开始识别")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start_ocr)
        self.start_btn.setEnabled(False)
        toolbar.addWidget(self.start_btn)

        toolbar.addStretch()

        self.save_btn = QPushButton("💾 保存结果")
        self.save_btn.setObjectName("secondary")
        self.save_btn.clicked.connect(self._save_results)
        self.save_btn.setEnabled(False)
        toolbar.addWidget(self.save_btn)

        layout.addLayout(toolbar)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("就绪")
        layout.addWidget(self.progress)

        # 主内容区 — 左右分栏
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：图片列表 + 预览
        left_panel = QFrame()
        left_panel.setObjectName("card")
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("📷 截图列表"))
        self.file_list = QListWidget()
        self.file_list.currentItemChanged.connect(self._preview_image)
        left_layout.addWidget(self.file_list)

        self.image_preview = QLabel("选择图片预览")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumHeight(200)
        self.image_preview.setStyleSheet(f"""
            background-color: {COLORS['input_bg']};
            border: 1px dashed {COLORS['border']};
            border-radius: 8px;
            padding: 16px;
            color: {COLORS['text_dim']};
        """)
        left_layout.addWidget(self.image_preview)

        splitter.addWidget(left_panel)

        # 右侧：识别结果
        right_panel = QFrame()
        right_panel.setObjectName("card")
        right_layout = QVBoxLayout(right_panel)

        result_header = QHBoxLayout()
        result_header.addWidget(QLabel("💬 识别结果"))
        self.result_count = QLabel("0 条消息")
        self.result_count.setStyleSheet(f"color: {COLORS['text_dim']};")
        result_header.addStretch()
        result_header.addWidget(self.result_count)
        right_layout.addLayout(result_header)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 11))
        right_layout.addWidget(self.result_text)

        # 日志
        right_layout.addWidget(QLabel("📋 运行日志"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet(f"background-color: {COLORS['input_bg']};")
        right_layout.addWidget(self.log_text)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

    def _select_dir(self):
        """选择截图目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择截图目录")
        if dir_path:
            self._load_images_from_dir(Path(dir_path))

    def _add_files(self):
        """添加图片文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择截图文件", "",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp);;所有文件 (*)"
        )
        if files:
            for f in files:
                self._add_image(Path(f))

    def _load_images_from_dir(self, dir_path: Path):
        """从目录加载图片"""
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        self.image_paths = sorted([
            f for f in dir_path.iterdir()
            if f.suffix.lower() in exts
        ])

        self.file_list.clear()
        for p in self.image_paths:
            self.file_list.addItem(QListWidgetItem(f"📷 {p.name}"))

        self.start_btn.setEnabled(len(self.image_paths) > 0)
        logger.info(f"加载 {len(self.image_paths)} 张截图")

    def _add_image(self, path: Path):
        """添加单张图片"""
        if path not in self.image_paths:
            self.image_paths.append(path)
            self.file_list.addItem(QListWidgetItem(f"📷 {path.name}"))
            self.start_btn.setEnabled(True)

    def _preview_image(self, current, previous):
        """预览选中的图片"""
        if not current:
            return
        idx = self.file_list.row(current)
        if 0 <= idx < len(self.image_paths):
            pixmap = QPixmap(str(self.image_paths[idx]))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    400, 300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled)

    def _start_ocr(self):
        """开始 OCR 识别"""
        if not self.image_paths:
            return

        engine = self.engine_combo.currentText()
        self.start_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log_text.clear()
        self.result_text.clear()

        self.worker = OCRWorker(self.base_dir, self.image_paths, engine)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.log.connect(self._on_log)
        self.worker.start()

    def _on_progress(self, current, total):
        pct = int(current / total * 100)
        self.progress.setValue(pct)
        self.progress.setFormat(f"{current}/{total} ({pct}%)")

    def _on_finished(self, results):
        self.results = results
        self.start_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.result_count.setText(f"{len(results)} 条消息")

        # 显示结果
        lines = []
        for msg in results:
            role = "我" if msg.get("role") == "me" else "TA"
            text = msg.get("text", "")
            source = msg.get("source", "")
            lines.append(f"[{role}] {text}  ({source})")
        self.result_text.setPlainText("\n".join(lines))

        logger.info(f"OCR 完成: {len(results)} 条消息")
        self._on_log(f"✅ 识别完成: {len(results)} 条消息")

    def _on_error(self, error):
        self.start_btn.setEnabled(True)
        self._on_log(f"❌ 错误: {error}")
        logger.error(f"OCR 失败: {error}")

    def _on_log(self, msg):
        self.log_text.append(msg)

    def _save_results(self):
        """保存结果"""
        if not self.results:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "保存识别结果", "data/chat_log.json",
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            self._on_log(f"💾 已保存: {path}")
