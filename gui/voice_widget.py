#!/usr/bin/env python3
"""声音克隆页面 — 可视化预览"""

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QComboBox, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QSlider
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from gui.styles import COLORS
from gui.logger import get_logger

logger = get_logger("voice")


class VoiceWorker(QThread):
    """声音克隆工作线程"""
    finished = pyqtSignal(str)  # output_dir
    error = pyqtSignal(str)
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, base_dir, audio_files, engine, output_dir):
        super().__init__()
        self.base_dir = base_dir
        self.audio_files = audio_files
        self.engine = engine
        self.output_dir = output_dir

    def run(self):
        try:
            import sys, asyncio
            sys.path.insert(0, str(self.base_dir))
            from voice_clone import VoiceCloner

            config_path = self.base_dir / "config.json"
            with open(config_path, "r") as f:
                config = json.load(f)

            cloner = VoiceCloner(config, self.engine)
            self.log.emit(f"引擎: {self.engine}")
            self.log.emit(f"样本数: {len(self.audio_files)}")

            asyncio.run(cloner.train(self.audio_files, Path(self.output_dir)))
            self.finished.emit(self.output_dir)
        except Exception as e:
            self.error.emit(str(e))


class VoiceWidget(QWidget):
    """声音克隆页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.audio_files = []
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🎤 声音克隆")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("从语音样本中克隆声音，支持 OpenVoice (CPU) 和 GPT-SoVITS (GPU)")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.add_btn = QPushButton("📁 添加语音文件")
        self.add_btn.setObjectName("secondary")
        self.add_btn.clicked.connect(self._add_files)
        toolbar.addWidget(self.add_btn)

        self.dir_btn = QPushButton("📂 选择目录")
        self.dir_btn.setObjectName("secondary")
        self.dir_btn.clicked.connect(self._select_dir)
        toolbar.addWidget(self.dir_btn)

        toolbar.addWidget(QLabel("引擎:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["openvoice", "gptsovits"])
        self.engine_combo.setFixedWidth(140)
        toolbar.addWidget(self.engine_combo)

        self.train_btn = QPushButton("🚀 开始训练")
        self.train_btn.setObjectName("primary")
        self.train_btn.clicked.connect(self._train)
        self.train_btn.setEnabled(False)
        toolbar.addWidget(self.train_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # 文件列表
        list_frame = QFrame()
        list_frame.setObjectName("card")
        list_layout = QVBoxLayout(list_frame)

        list_header = QHBoxLayout()
        list_header.addWidget(QLabel("🎵 语音样本"))
        self.file_count = QLabel("0 个文件")
        self.file_count.setStyleSheet(f"color: {COLORS['text_dim']};")
        list_header.addStretch()
        list_header.addWidget(self.file_count)
        list_layout.addLayout(list_header)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(200)
        list_layout.addWidget(self.file_list)

        layout.addWidget(list_frame)

        # 音频预览
        preview_frame = QFrame()
        preview_frame.setObjectName("card")
        preview_layout = QVBoxLayout(preview_frame)

        preview_layout.addWidget(QLabel("🔊 音频预览"))

        btn_row = QHBoxLayout()
        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.setObjectName("secondary")
        self.play_btn.clicked.connect(self._play)
        self.play_btn.setEnabled(False)
        btn_row.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setObjectName("secondary")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setEnabled(False)
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()
        preview_layout.addLayout(btn_row)

        self.audio_info = QLabel("选择文件后点击播放预览")
        self.audio_info.setStyleSheet(f"color: {COLORS['text_dim']};")
        preview_layout.addWidget(self.audio_info)

        layout.addWidget(preview_frame)

        # 日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet(f"background-color: {COLORS['input_bg']};")
        layout.addWidget(self.log_text)

        # 媒体播放器
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择语音文件", "",
            "音频文件 (*.wav *.mp3 *.ogg *.m4a *.amr *.silk *.flac);;所有文件 (*)"
        )
        for f in files:
            p = Path(f)
            if p not in self.audio_files:
                self.audio_files.append(p)
                self.file_list.addItem(QListWidgetItem(f"🎵 {p.name} ({p.stat().st_size // 1024}KB)"))

        self.file_count.setText(f"{len(self.audio_files)} 个文件")
        self.train_btn.setEnabled(len(self.audio_files) > 0)
        self.play_btn.setEnabled(len(self.audio_files) > 0)

    def _select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择语音目录")
        if dir_path:
            exts = {".wav", ".mp3", ".ogg", ".m4a", ".amr", ".silk", ".flac"}
            self.audio_files = sorted([
                f for f in Path(dir_path).iterdir()
                if f.suffix.lower() in exts
            ])
            self.file_list.clear()
            for p in self.audio_files:
                self.file_list.addItem(QListWidgetItem(f"🎵 {p.name} ({p.stat().st_size // 1024}KB)"))
            self.file_count.setText(f"{len(self.audio_files)} 个文件")
            self.train_btn.setEnabled(len(self.audio_files) > 0)
            self.play_btn.setEnabled(len(self.audio_files) > 0)

    def _play(self):
        current = self.file_list.currentRow()
        if 0 <= current < len(self.audio_files):
            self.player.setSource(self.audio_files[current].as_uri())
            self.audio_output.setVolume(80)
            self.player.play()
            self.play_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.audio_info.setText(f"▶️ 播放: {self.audio_files[current].name}")

    def _stop(self):
        self.player.stop()
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.audio_info.setText("已停止")

    def _train(self):
        if not self.audio_files:
            return

        engine = self.engine_combo.currentText()
        output_dir = str(self.base_dir / "data" / "voice_model")

        self.train_btn.setEnabled(False)
        self.progress.setValue(0)

        self.worker = VoiceWorker(self.base_dir, self.audio_files, engine, output_dir)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.log.connect(lambda m: self.log_text.append(m))
        self.worker.progress.connect(lambda c, t: self.progress.setValue(int(c / t * 100)))
        self.worker.start()

    def _on_finished(self, output_dir):
        self.train_btn.setEnabled(True)
        self.progress.setValue(100)
        self.log_text.append(f"✅ 声音模型已保存: {output_dir}")
        logger.info(f"声音训练完成: {output_dir}")

    def _on_error(self, error):
        self.train_btn.setEnabled(True)
        self.log_text.append(f"❌ 训练失败: {error}")
        logger.error(f"声音训练失败: {error}")
