@echo off
REM 🫀 复活吧我的赛博前任 — 一键启动脚本 (Windows)

title 复活吧我的赛博前任 v1.2.0

echo 🫀 复活吧我的赛博前任 — Cyber Ex Resurrection v1.2.0
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REM 检查 Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ Python 未安装
    echo    请访问 https://www.python.org/downloads/
    echo    安装时勾选 "Add Python to PATH"
    pause
    exit /b 1
)

python --version
echo ✅ Python 就绪

REM 检查依赖
echo.
echo 📦 检查依赖...
python -c "import PyQt6" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ⚙️  安装 PyQt6...
    pip install PyQt6 PyQt6-sip -q
)

python -c "import click, rich" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ⚙️  安装基础依赖...
    pip install click rich -q
)

echo ✅ 依赖就绪

REM 创建目录
if not exist data\screenshots mkdir data\screenshots
if not exist data\voices mkdir data\voices
if not exist data\voice_model mkdir data\voice_model
if not exist data\memory mkdir data\memory
if not exist data\logs mkdir data\logs
if not exist data\imported mkdir data\imported

REM 启动
echo.
echo 🚀 启动图形界面...
python gui_app.py

pause
