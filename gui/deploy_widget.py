#!/usr/bin/env python3
"""一键部署页面 — 自动化完整流程"""

import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QCheckBox, QProgressBar, QTextEdit,
    QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from gui.styles import COLORS
from gui.logger import get_logger

logger = get_logger("deploy")


class DeployWorker(QThread):
    """一键部署工作线程"""
    stage_changed = pyqtSignal(str, str)  # (stage_name, status)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, base_dir, config):
        super().__init__()
        self.base_dir = base_dir
        self.config = config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        import sys, asyncio
        sys.path.insert(0, str(self.base_dir))
        results = {}
        total_steps = sum([
            self.config.get("ocr_enabled", False),
            self.config.get("import_enabled", False),
            self.config.get("clean_enabled", True),
            self.config.get("persona_enabled", True),
            self.config.get("voice_enabled", False),
            self.config.get("bot_enabled", False),
        ])
        current_step = 0

        try:
            with open(self.base_dir / "config.json", "r") as f:
                app_config = json.load(f)

            # Step 1: OCR 或 Import
            if self.config.get("import_enabled") and self.config.get("import_path"):
                self.stage_changed.emit("导入聊天记录", "running")
                self.log.emit(f"📥 导入: {self.config['import_path']}")
                from importers import ChatImporter
                path = Path(self.config["import_path"])
                if path.is_dir():
                    messages = ChatImporter.import_directory(path)
                else:
                    messages = ChatImporter.import_file(path)
                out = self.base_dir / "data" / "chat_log.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)
                results["import"] = {"count": len(messages), "output": str(out)}
                self.log.emit(f"✅ 导入 {len(messages)} 条消息")
                self.stage_changed.emit("导入聊天记录", "done")
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100))

            elif self.config.get("ocr_enabled") and self.config.get("screenshot_dir"):
                self.stage_changed.emit("截图 OCR", "running")
                self.log.emit(f"📸 OCR: {self.config['screenshot_dir']}")
                from ocr_engines import MultiEngineOCR
                engine = self.config.get("ocr_engine", "mimo_omni")
                ocr = MultiEngineOCR(app_config, [engine])
                sp = Path(self.config["screenshot_dir"])
                exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
                screenshots = sorted([f for f in sp.iterdir() if f.suffix.lower() in exts])
                messages = []
                for img in screenshots:
                    if self._cancelled:
                        return
                    try:
                        results_list = ocr.recognize(img)
                        messages.extend(results_list)
                    except Exception as e:
                        self.log.emit(f"⚠️ {img.name}: {e}")
                out = self.base_dir / "data" / "chat_log.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)
                results["ocr"] = {"count": len(messages), "output": str(out)}
                self.log.emit(f"✅ OCR {len(messages)} 条消息")
                self.stage_changed.emit("截图 OCR", "done")
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100))

            if self._cancelled:
                return

            # Step 2: Clean
            if self.config.get("clean_enabled", True):
                self.stage_changed.emit("数据清洗", "running")
                self.log.emit("🧹 清洗数据...")
                from data_cleaner import clean_chat_file
                chat_in = self.base_dir / "data" / "chat_log.json"
                chat_out = self.base_dir / "data" / "chat_log_cleaned.json"
                if chat_in.exists():
                    clean_chat_file(chat_in, chat_out, app_config)
                    results["clean"] = {"output": str(chat_out)}
                self.log.emit("✅ 清洗完成")
                self.stage_changed.emit("数据清洗", "done")
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100))

            if self._cancelled:
                return

            # Step 3: Persona
            if self.config.get("persona_enabled", True):
                self.stage_changed.emit("人格建模", "running")
                self.log.emit("🧠 生成人格...")
                from persona_builder import PersonaBuilder
                builder = PersonaBuilder(app_config)
                chat_file = self.base_dir / "data" / "chat_log_cleaned.json"
                if not chat_file.exists():
                    chat_file = self.base_dir / "data" / "chat_log.json"
                if chat_file.exists():
                    persona_text = asyncio.run(builder.build(chat_file))
                    persona_path = self.base_dir / "data" / "persona.md"
                    with open(persona_path, "w", encoding="utf-8") as f:
                        f.write(persona_text)
                    results["persona"] = {"length": len(persona_text), "output": str(persona_path)}
                    self.log.emit(f"✅ 人格生成完成 ({len(persona_text)} 字符)")
                self.stage_changed.emit("人格建模", "done")
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100))

            if self._cancelled:
                return

            # Step 4: Voice
            if self.config.get("voice_enabled") and self.config.get("voice_dir"):
                self.stage_changed.emit("声音克隆", "running")
                self.log.emit("🎤 训练声音...")
                from voice_clone import VoiceCloner
                engine = self.config.get("voice_engine", "openvoice")
                cloner = VoiceCloner(app_config, engine)
                vp = Path(self.config["voice_dir"])
                exts = {".wav", ".mp3", ".ogg", ".m4a", ".amr", ".silk", ".flac"}
                audio_files = sorted([f for f in vp.iterdir() if f.suffix.lower() in exts])
                output_dir = self.base_dir / "data" / "voice_model"
                asyncio.run(cloner.train(audio_files, output_dir))
                results["voice"] = {"engine": engine, "samples": len(audio_files)}
                self.log.emit(f"✅ 声音训练完成 ({engine})")
                self.stage_changed.emit("声音克隆", "done")
                current_step += 1
                self.progress.emit(int(current_step / total_steps * 100))

            if self._cancelled:
                return

            # Step 5: Bot
            if self.config.get("bot_enabled") and self.config.get("bot_platform"):
                self.stage_changed.emit("启动机器人", "running")
                platform = self.config["bot_platform"]
                self.log.emit(f"📱 启动 {platform} 机器人...")
                from bots import get_bot
                BotClass = get_bot(platform)
                bot_config = app_config.get("bots", {}).get(platform, {})
                bot = BotClass(app_config, bot_config, str(self.base_dir / "data" / "persona.md"),
                              str(self.base_dir / "data" / "voice_model"),
                              self.config.get("voice_engine", "openvoice"))
                results["bot"] = {"platform": platform, "class": BotClass.__name__}
                self.log.emit(f"✅ {platform} 机器人就绪")
                self.stage_changed.emit("启动机器人", "done")
                current_step += 1
                self.progress.emit(100)

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


class DeployWidget(QWidget):
    """一键部署页面"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🚀 一键部署")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("自动执行完整流程：导入/OCR → 清洗 → 人格 → 声音 → 机器人")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # 数据源选择
        source_group = QGroupBox("📥 数据源")
        source_layout = QVBoxLayout(source_group)

        # Import
        import_row = QHBoxLayout()
        self.import_check = QCheckBox("导入聊天记录文件")
        import_row.addWidget(self.import_check)
        self.import_path_label = QLabel("未选择")
        self.import_path_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        import_row.addWidget(self.import_path_label)
        self.import_btn = QPushButton("选择文件")
        self.import_btn.setObjectName("secondary")
        self.import_btn.clicked.connect(self._select_import)
        import_row.addWidget(self.import_btn)
        source_layout.addLayout(import_row)

        # OCR
        ocr_row = QHBoxLayout()
        self.ocr_check = QCheckBox("从截图 OCR 提取")
        ocr_row.addWidget(self.ocr_check)
        self.screenshot_label = QLabel("未选择")
        self.screenshot_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        ocr_row.addWidget(self.screenshot_label)
        self.screenshot_btn = QPushButton("选择目录")
        self.screenshot_btn.setObjectName("secondary")
        self.screenshot_btn.clicked.connect(self._select_screenshots)
        ocr_row.addWidget(self.screenshot_btn)

        ocr_row.addWidget(QLabel("引擎:"))
        self.ocr_engine = QComboBox()
        self.ocr_engine.addItems(["mimo_omni", "paddleocr", "easyocr"])
        self.ocr_engine.setFixedWidth(120)
        ocr_row.addWidget(self.ocr_engine)
        source_layout.addLayout(ocr_row)

        layout.addWidget(source_group)

        # 流程选项
        steps_group = QGroupBox("🔄 部署步骤")
        steps_layout = QVBoxLayout(steps_group)

        self.clean_check = QCheckBox("🧹 数据清洗 (过滤系统消息/广告/重复)")
        self.clean_check.setChecked(True)
        steps_layout.addWidget(self.clean_check)

        self.persona_check = QCheckBox("🧠 人格建模 (提取语言风格)")
        self.persona_check.setChecked(True)
        steps_layout.addWidget(self.persona_check)

        voice_row = QHBoxLayout()
        self.voice_check = QCheckBox("🎤 声音克隆")
        voice_row.addWidget(self.voice_check)
        self.voice_dir_label = QLabel("未选择")
        self.voice_dir_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        voice_row.addWidget(self.voice_dir_label)
        self.voice_dir_btn = QPushButton("选择语音目录")
        self.voice_dir_btn.setObjectName("secondary")
        self.voice_dir_btn.clicked.connect(self._select_voice)
        voice_row.addWidget(self.voice_dir_btn)

        voice_row.addWidget(QLabel("引擎:"))
        self.voice_engine = QComboBox()
        self.voice_engine.addItems(["openvoice", "gptsovits"])
        self.voice_engine.setFixedWidth(120)
        voice_row.addWidget(self.voice_engine)
        steps_layout.addLayout(voice_row)

        bot_row = QHBoxLayout()
        self.bot_check = QCheckBox("📱 启动 IM 机器人")
        bot_row.addWidget(self.bot_check)
        self.bot_platform = QComboBox()
        self.bot_platform.addItems(["wechat", "qq", "feishu", "whatsapp"])
        self.bot_platform.setFixedWidth(120)
        bot_row.addWidget(self.bot_platform)
        bot_row.addStretch()
        steps_layout.addLayout(bot_row)

        layout.addWidget(steps_group)

        # 执行按钮
        btn_layout = QHBoxLayout()

        self.deploy_btn = QPushButton("🚀 开始部署")
        self.deploy_btn.setObjectName("primary")
        self.deploy_btn.setFixedHeight(48)
        self.deploy_btn.setFont(QFont("", 14))
        self.deploy_btn.clicked.connect(self._deploy)
        btn_layout.addWidget(self.deploy_btn)

        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setFixedHeight(48)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        # 进度
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # 阶段状态
        self.stages_frame = QFrame()
        self.stages_frame.setObjectName("card")
        self.stages_layout = QVBoxLayout(self.stages_frame)
        self.stages_labels = {}
        layout.addWidget(self.stages_frame)

        # 日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(f"background-color: {COLORS['input_bg']};")
        layout.addWidget(self.log_text)

    def _select_import(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "选择聊天记录", "",
            "所有支持格式 (*.json *.csv *.html *.txt *.db);;所有文件 (*)"
        )
        if file:
            self.import_path = file
            self.import_path_label.setText(Path(file).name)
            self.import_check.setChecked(True)

    def _select_screenshots(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择截图目录")
        if dir_path:
            self.screenshot_dir = dir_path
            count = len(list(Path(dir_path).glob("*")))
            self.screenshot_label.setText(f"{count} 个文件")
            self.ocr_check.setChecked(True)

    def _select_voice(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择语音目录")
        if dir_path:
            self.voice_dir = dir_path
            exts = {".wav", ".mp3", ".ogg", ".m4a", ".amr", ".silk", ".flac"}
            count = len([f for f in Path(dir_path).iterdir() if f.suffix.lower() in exts])
            self.voice_dir_label.setText(f"{count} 个文件")
            self.voice_check.setChecked(True)

    def _deploy(self):
        config = {
            "import_enabled": self.import_check.isChecked(),
            "import_path": getattr(self, "import_path", ""),
            "ocr_enabled": self.ocr_check.isChecked(),
            "screenshot_dir": getattr(self, "screenshot_dir", ""),
            "ocr_engine": self.ocr_engine.currentText(),
            "clean_enabled": self.clean_check.isChecked(),
            "persona_enabled": self.persona_check.isChecked(),
            "voice_enabled": self.voice_check.isChecked(),
            "voice_dir": getattr(self, "voice_dir", ""),
            "voice_engine": self.voice_engine.currentText(),
            "bot_enabled": self.bot_check.isChecked(),
            "bot_platform": self.bot_platform.currentText(),
        }

        self.deploy_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log_text.clear()
        self.progress.setValue(0)

        # 清除旧的阶段状态
        for i in reversed(range(self.stages_layout.count())):
            self.stages_layout.itemAt(i).widget().setParent(None)
        self.stages_labels.clear()

        self.worker = DeployWorker(self.base_dir, config)
        self.worker.stage_changed.connect(self._on_stage_changed)
        self.worker.progress.connect(lambda p: self.progress.setValue(p))
        self.worker.log.connect(lambda m: self.log_text.append(m))
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
            self.log_text.append("❌ 已取消部署")

    def _on_stage_changed(self, stage, status):
        if stage not in self.stages_labels:
            label = QLabel()
            self.stages_layout.addWidget(label)
            self.stages_labels[stage] = label

        label = self.stages_labels[stage]
        if status == "running":
            label.setText(f"⏳ {stage} — 进行中...")
            label.setStyleSheet(f"color: {COLORS['warning']};")
        elif status == "done":
            label.setText(f"✅ {stage} — 完成")
            label.setStyleSheet(f"color: {COLORS['success']};")

    def _on_finished(self, results):
        self.deploy_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setValue(100)
        self.log_text.append("\n🎉 部署完成！")
        for stage, data in results.items():
            self.log_text.append(f"  ✅ {stage}: {data}")
        logger.info(f"部署完成: {results}")

    def _on_error(self, error):
        self.deploy_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.log_text.append(f"\n❌ 部署失败: {error}")
        logger.error(f"部署失败: {error}")
