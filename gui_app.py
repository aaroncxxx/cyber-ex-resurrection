#!/usr/bin/env python3
"""
复活吧我的赛博前任 — GUI 主入口
Cross-platform PyQt6 GUI
"""

import sys
import os
from pathlib import Path

# 确保当前目录在 path 中
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame, QSizePolicy,
    QSplashScreen
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor

from gui.styles import APP_STYLESHEET, COLORS
from gui.dashboard import DashboardWidget
from gui.ocr_widget import OCRWidget
from gui.import_widget import ImportWidget
from gui.persona_widget import PersonaWidget
from gui.voice_widget import VoiceWidget
from gui.deploy_widget import DeployWidget
from gui.destroy_widget import DestroyWidget
from gui.log_widget import LogWidget
from gui.consent_widget import ConsentWidget
from gui.logger import setup_gui_logger


class NavButton(QPushButton):
    """导航按钮"""

    def __init__(self, text, icon_text="", parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}" if icon_text else f"  {text}")
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("navButton")


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🫀 复活吧我的赛博前任 — Cyber Ex Resurrection v1.2.0")
        self.setMinimumSize(1100, 720)
        self.resize(1200, 780)

        # 设置日志
        self.logger = setup_gui_logger(BASE_DIR)

        # 中心组件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 侧边导航栏 ──
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        nav_frame.setFixedWidth(200)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 16, 8, 16)
        nav_layout.setSpacing(4)

        # Logo
        logo = QLabel("🫀 赛博前任")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(logo)
        nav_layout.addSpacing(16)

        # 导航按钮
        self.nav_buttons = []
        nav_items = [
            ("仪表盘", "📊", 0),
            ("伦理声明", "⚖️", 1),
            ("截图识别", "📸", 2),
            ("导入记录", "📥", 3),
            ("数据清洗", "🧹", 4),
            ("人格预览", "🧠", 5),
            ("声音克隆", "🎤", 6),
            ("一键部署", "🚀", 7),
            ("数据销毁", "🔥", 8),
            ("运行日志", "📋", 9),
        ]

        for text, icon, index in nav_items:
            btn = NavButton(text, icon)
            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()

        # 版本标签
        ver = QLabel("v1.2.0")
        ver.setObjectName("version")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(ver)

        main_layout.addWidget(nav_frame)

        # ── 内容区 ──
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentStack")

        # 创建各页面
        self.dashboard = DashboardWidget(BASE_DIR)
        self.consent = ConsentWidget(BASE_DIR)
        self.ocr = OCRWidget(BASE_DIR)
        self.import_widget = ImportWidget(BASE_DIR)
        self.persona = PersonaWidget(BASE_DIR)
        self.voice = VoiceWidget(BASE_DIR)
        self.deploy = DeployWidget(BASE_DIR)
        self.destroy_widget = DestroyWidget(BASE_DIR)
        self.log_widget = LogWidget(BASE_DIR)

        # 数据清洗页面复用 import_widget 的 clean 部分
        from gui.clean_widget import CleanWidget
        self.clean_widget = CleanWidget(BASE_DIR)

        self.stack.addWidget(self.dashboard)      # 0
        self.stack.addWidget(self.consent)         # 1
        self.stack.addWidget(self.ocr)             # 2
        self.stack.addWidget(self.import_widget)   # 3
        self.stack.addWidget(self.clean_widget)    # 4
        self.stack.addWidget(self.persona)         # 5
        self.stack.addWidget(self.voice)           # 6
        self.stack.addWidget(self.deploy)          # 7
        self.stack.addWidget(self.destroy_widget)  # 8
        self.stack.addWidget(self.log_widget)      # 9

        main_layout.addWidget(self.stack)

        # 默认选中仪表盘
        self.nav_buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)

        # 连接页面切换信号
        self.stack.currentChanged.connect(self._on_page_changed)

    def switch_page(self, index):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _on_page_changed(self, index):
        """页面切换回调"""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    app.setApplicationName("Cyber Ex Resurrection")
    app.setApplicationVersion("1.1.1")

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
