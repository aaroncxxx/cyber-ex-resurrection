#!/usr/bin/env python3
"""GUI 样式表 — 暗色主题"""

COLORS = {
    "bg": "#1a1a2e",
    "bg_light": "#16213e",
    "bg_card": "#1e2a4a",
    "accent": "#e94560",
    "accent_hover": "#ff6b81",
    "text": "#eaeaea",
    "text_dim": "#8892a8",
    "success": "#2ed573",
    "warning": "#ffa502",
    "error": "#ff4757",
    "border": "#2a3a5e",
    "input_bg": "#0f1629",
    "nav_bg": "#0f1629",
    "nav_active": "#e94560",
}

APP_STYLESHEET = f"""
/* ── 全局 ── */
QMainWindow {{
    background-color: {COLORS['bg']};
}}
QWidget {{
    color: {COLORS['text']};
    font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
}}

/* ── 导航栏 ── */
#navFrame {{
    background-color: {COLORS['nav_bg']};
    border-right: 1px solid {COLORS['border']};
}}
#logo {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['accent']};
    padding: 8px;
}}
#version {{
    color: {COLORS['text_dim']};
    font-size: 11px;
}}
#navButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {COLORS['text_dim']};
    font-size: 13px;
    text-align: left;
    padding: 0 16px;
}}
#navButton:hover {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
}}
#navButton:checked {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: bold;
}}

/* ── 内容区 ── */
#contentStack {{
    background-color: {COLORS['bg']};
}}

/* ── 卡片 ── */
QFrame#card {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 16px;
}}
QFrame#card:hover {{
    border-color: {COLORS['accent']};
}}

/* ── 标签 ── */
QLabel#title {{
    font-size: 22px;
    font-weight: bold;
    color: {COLORS['text']};
}}
QLabel#subtitle {{
    font-size: 14px;
    color: {COLORS['text_dim']};
}}
QLabel#stat_value {{
    font-size: 32px;
    font-weight: bold;
    color: {COLORS['accent']};
}}
QLabel#stat_label {{
    font-size: 12px;
    color: {COLORS['text_dim']};
}}

/* ── 按钮 ── */
QPushButton#primary {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
}}
QPushButton#primary:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton#primary:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_dim']};
}}
QPushButton#secondary {{
    background-color: transparent;
    color: {COLORS['accent']};
    border: 1px solid {COLORS['accent']};
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
}}
QPushButton#secondary:hover {{
    background-color: {COLORS['accent']};
    color: white;
}}
QPushButton#danger {{
    background-color: {COLORS['error']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
}}
QPushButton#danger:hover {{
    background-color: #ff6b6b;
}}

/* ── 输入框 ── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS['accent']};
}}

/* ── 下拉框 ── */
QComboBox {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {COLORS['text']};
    min-width: 120px;
}}
QComboBox::drop-down {{
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent']};
}}

/* ── 进度条 ── */
QProgressBar {{
    background-color: {COLORS['input_bg']};
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: {COLORS['text']};
    font-size: 10px;
}}
QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 6px;
}}

/* ── 列表 ── */
QListWidget {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    color: {COLORS['text']};
}}
QListWidget::item {{
    padding: 8px;
    border-bottom: 1px solid {COLORS['border']};
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}

/* ── 表格 ── */
QTableWidget {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    gridline-color: {COLORS['border']};
    color: {COLORS['text']};
}}
QTableWidget::item {{
    padding: 6px;
}}
QHeaderView::section {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: none;
    border-bottom: 2px solid {COLORS['accent']};
    padding: 8px;
    font-weight: bold;
}}

/* ── 复选框 ── */
QCheckBox {{
    color: {COLORS['text']};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['input_bg']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}

/* ── 分组框 ── */
QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: {COLORS['text']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: {COLORS['accent']};
}}

/* ── 滚动条 ── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-width: 30px;
}}

/* ── 选项卡 ── */
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['bg_card']};
}}
QTabBar::tab {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 20px;
    color: {COLORS['text_dim']};
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['accent']};
    font-weight: bold;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {COLORS['border']};
    width: 2px;
}}
"""
