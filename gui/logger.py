#!/usr/bin/env python3
"""GUI 日志系统"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import QObject, pyqtSignal


class LogSignal(QObject):
    """日志信号，用于线程安全地更新 GUI"""
    log_added = pyqtSignal(str, str)  # (level, message)


class GUILogHandler(logging.Handler):
    """GUI 日志处理器"""

    def __init__(self, signal: LogSignal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.log_added.emit(record.levelname, msg)


# 全局信号
log_signal = LogSignal()


def setup_gui_logger(base_dir: Path) -> logging.Logger:
    """设置 GUI 日志系统"""
    logger = logging.getLogger("CyberEx")
    logger.setLevel(logging.DEBUG)

    # 日志目录
    log_dir = base_dir / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 文件日志 — 10MB × 5
    file_handler = RotatingFileHandler(
        log_dir / "gui.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # GUI 日志
    gui_handler = GUILogHandler(log_signal)
    gui_handler.setLevel(logging.INFO)
    gui_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    ))

    # 控制台日志
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s"
    ))

    logger.addHandler(file_handler)
    logger.addHandler(gui_handler)
    logger.addHandler(console_handler)

    logger.info("GUI 日志系统初始化完成")
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """获取子 logger"""
    base = logging.getLogger("CyberEx")
    if name:
        return base.getChild(name)
    return base
