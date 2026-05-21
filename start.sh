#!/bin/bash
# 🫀 复活吧我的赛博前任 — 一键启动脚本
# Cross-platform: macOS / Linux

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🫀 复活吧我的赛博前任 — Cyber Ex Resurrection v1.2.0"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    echo "   macOS: brew install python3"
    echo "   Linux: sudo apt install python3 python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "✅ $PYTHON_VERSION"

# 检查依赖
echo ""
echo "📦 检查依赖..."
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "⚙️  安装 PyQt6..."
    pip3 install PyQt6 PyQt6-sip -q
fi

if ! python3 -c "import click, rich" 2>/dev/null; then
    echo "⚙️  安装基础依赖..."
    pip3 install click rich -q
fi

echo "✅ 依赖就绪"

# 创建必要目录
mkdir -p data/screenshots data/voices data/voice_model data/memory data/logs data/imported

# 启动 GUI
echo ""
echo "🚀 启动图形界面..."
python3 gui_app.py
