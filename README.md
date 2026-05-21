# 🫀 复活吧我的赛博前任

> 导入聊天截图 + 语音文件 → 克隆前任的人格与声音 → 通过微信/QQ/飞书/WhatsApp 复活 TA

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/Version-1.2.0-orange)

---

## ⚠️ 法律风险提示

**使用前请务必阅读：**

本工具涉及个人隐私数据处理和 AI 人格克隆，使用不当可能触犯法律：

| 法律法规 | 相关条款 | 违反后果 |
|---------|---------|---------|
| 《民法典》第1019条 | 禁止伪造侵害肖像权 | 民事赔偿 |
| 《民法典》第1034条 | 个人信息保护 | 民事赔偿 |
| 《个人信息保护法》第14条 | 处理个人信息需同意 | 行政处罚 |
| 《刑法》第253条之一 | 侵犯公民个人信息罪 | **刑事处罚** |
| GDPR 第17条 | 被遗忘权（数据删除权） | 高额罚款 |
| 各州 Deepfake 法案 | 禁止深度伪造 | 刑事处罚 |

**首次使用必须运行伦理确认：**
```bash
python3 main.py consent          # 确认伦理条款
python3 main.py consent --show-legal  # 查看完整法律条文
```

---

## 📖 这是什么？

一个能让你的「电子前任」复活的 AI 工具。

**你只需要准备：**
1. 📸 你和 TA 的聊天截图（微信/QQ/短信都行）或导出文件
2. 🎤 TA 的语音消息（微信语音条、录音等）

**它能做什么：**
- 从截图/导出文件中读懂 TA 的说话风格、口头禅、性格
- 从语音中克隆 TA 的声音
- 让 TA 在微信/QQ/飞书/WhatsApp 上"复活"，像真人一样跟你聊天
- **有记忆**：记住聊过的事，越聊越像 TA
- **一键销毁**：随时安全删除所有本地数据

---

## 🖥️ 图形界面（推荐）

```bash
# macOS / Linux
./start.sh

# Windows
start.bat

# 或直接
python3 gui_app.py
```

GUI 功能：
- 📊 仪表盘 — 实时数据总览
- ⚖️ 伦理声明 — 可视化确认流程
- 📸 截图识别 — 多引擎选择 + 图片预览
- 📥 导入记录 — 支持多种格式 + 表格预览
- 🧹 数据清洗 — 选项配置 + 实时预览
- 🧠 人格预览 — 聊天记录 vs 人格模型对比
- 🎤 声音克隆 — 音频试听 + 训练进度
- 🚀 一键部署 — 步骤配置 + 进度追踪
- 🔥 数据销毁 — 扫描预览 + 安全销毁
- 📋 运行日志 — 实时日志 + 级别过滤

---

## 🚀 快速开始

### 第一步：安装 Python

**Windows 用户：**
1. 打开 https://www.python.org/downloads/
2. 点击 "Download Python 3.x.x"
3. 安装时**勾选 "Add Python to PATH"** ✅

**Mac 用户：**
```bash
brew install python3
```

### 第二步：安装依赖

```bash
cd skills/cyber-ex-resurrection
pip install -r requirements.txt

# 国内镜像加速
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 第三步：伦理确认（必须）

```bash
python3 main.py consent
```

首次使用会展示伦理声明和法律风险，你需要逐项确认才能继续。

### 第四步：配置 MIMO API

编辑 `config.json`，填入 MIMO API Key：
```json
{
  "mimo": {
    "api_key": "sk-你的API-Key",
    "endpoint": "https://api.xiaomimimo.com/v1"
  }
}
```

> 获取 API Key：https://platform.xiaomimimo.com → 控制台 → API Keys

---

## 📸 使用方法

### 方法一：一键 Pipeline（推荐）

```bash
# 从截图开始
python3 main.py pipeline -s data/screenshots/ -v data/voices/

# 或从导出文件开始
python3 main.py pipeline -f data/wechat_export.txt -v data/voices/

# 然后聊天
python3 main.py chat
```

### 方法三：一键部署（CLI）

```bash
# 从截图到机器人，全自动
python3 deploy.py --input data/screenshots/ --voices data/voices/ --platform wechat

# 从导入文件开始
python3 deploy.py --import-file data/wechat.txt --voices data/voices/

# 仅清洗数据
python3 deploy.py --import-file data/wechat.txt --clean-only
```

### 方法四：分步执行

```bash
# 1. 提取对话（选择引擎）
python3 main.py ocr -i data/screenshots/ --engine mimo_omni
# 或导入已有记录
python3 main.py import -i data/wechat.txt

# 2. 智能清洗
python3 main.py clean

# 3. 构建人格
python3 main.py persona

# 4. 训练声音
python3 main.py voice -i data/voices/

# 5. 聊天
python3 main.py chat
```

### 方法三：启动微信机器人

```bash
python3 main.py bot -p wechat
```

---

## 🔍 OCR 引擎

| 引擎 | 优势 | 安装 |
|------|------|------|
| `mimo_omni` | 语义理解最强，复杂截图 | 内置（需 API） |
| `paddleocr` | 手写体、竖排、特殊符号 | `pip install paddleocr` |
| `easyocr` | 多语言、表情包 | `pip install easyocr` |
| `multi` | 三引擎融合投票 | 安装以上全部 |

```bash
python3 main.py ocr -i data/screenshots/ --engine paddleocr
python3 main.py ocr -i data/screenshots/ --engine multi
```

---

## 📥 导入格式

支持多种聊天记录格式：

| 格式 | 示例 |
|------|------|
| JSON | `[{"role":"me","text":"你好"}]` |
| CSV | `role,text,time` 带标题行 |
| HTML | 微信导出的网页文件 |
| TXT (带时间戳) | `[2024-01-15 14:30] 我: 消息` |
| TXT (微信导出) | 带分隔线的导出格式 |
| SQLite | 手机备份数据库 |

```bash
python3 main.py import -i data/wechat.txt
python3 main.py import -i data/chat.csv
python3 main.py import -i data/backup.db
python3 main.py import -i data/chats/   # 整个目录
```

---

## 🧹 数据清洗

自动过滤：系统消息、广告、重复内容、无效对话、合并连续消息

```bash
python3 main.py clean                    # 默认清洗
python3 main.py clean --no-ads           # 保留广告
python3 main.py clean --keep-emoji-only  # 保留纯表情
```

---

## 🔥 一键数据销毁

```bash
python3 main.py destroy --scan   # 扫描本地数据（不删除）
python3 main.py destroy          # 安全销毁所有数据
```

安全流程：文件覆写（零填充）→ 删除，确保不可恢复。

---

## 🧠 记忆系统

| 层级 | 说明 | 持久性 |
|------|------|--------|
| 滑动窗口 | 最近 10 轮对话 | 会话内 |
| 关键事件 | 自动提取的重要信息 | 跨会话 |
| 持久记忆 | 序列化到文件 | 永久 |

---

## 💬 支持的平台

| 平台 | 状态 |
|------|------|
| 微信 | ✅（需 Wechaty Token） |
| QQ | ✅ |
| 飞书 | ✅ |
| WhatsApp | ✅ |
| CLI 聊天 | ✅ 默认 |

---

## 📁 项目结构

```
skills/cyber-ex-resurrection/
├── main.py               # 主入口
├── config.json           # 配置文件
├── requirements.txt      # 依赖
├── ethics.py             # ⚖️ 伦理声明 & 同意验证
├── data_destroy.py       # 🔥 一键数据销毁
├── ocr_extract.py        # 截图 OCR（MIMO Omni）
├── ocr_engines.py        # 🔍 多引擎 OCR（Paddle/Easy/MIMO）
├── importers.py          # 📥 多格式导入
├── data_cleaner.py       # 🧹 智能数据清洗
├── chat_parser.py        # 对话解析
├── persona_builder.py    # 人格建模
├── voice_clone.py        # 声音克隆
├── voice_tts.py          # 语音合成
├── chat_engine.py        # 对话引擎
├── memory.py             # 记忆系统
├── pipeline.py           # 统一管线
└── bots/                 # IM 机器人
```

---

## 📝 更新日志

### v1.2.0 (2026-05-21)
- 🖥️ **跨平台 GUI**：PyQt6 图形界面，支持 Windows/macOS/Linux，暗色主题
- 🚀 **一键部署 CLI**：`deploy.py` 命令行全自动，无需手动输入多个命令
- 📊 **仪表盘**：实时数据统计、快速操作入口、Pipeline 进度追踪
- ⚖️ **可视化伦理确认**：GUI 确认流程 + 法律条文展示
- 📸 **OCR 预览**：多引擎选择、图片预览、结果表格
- 🧠 **人格对比预览**：聊天记录 vs 人格模型左右分栏对比
- 🎤 **声音试听**：音频预览播放 + 训练进度可视化
- 🔥 **数据销毁增强**：扫描预览、选择性/全量销毁、安全覆写
- 📋 **日志系统**：实时日志流、级别过滤、文件导出、RotatingFileHandler
- ⚡ **启动脚本**：`start.sh` (macOS/Linux) / `start.bat` (Windows) 一键启动

### v1.1.1 (2026-05-21)
- ⚖️ 伦理合规：强制伦理声明、使用前同意确认、法律条文参考
- 🔥 一键数据销毁：安全覆写删除所有本地数据
- 🔍 多引擎 OCR：PaddleOCR + EasyOCR + MIMO Omni
- 📥 多格式导入：txt/csv/html/微信导出/手机备份
- 🧹 智能数据清洗：自动过滤系统消息、广告、重复内容

### v1.1.0 (2026-05-21)
- 🧠 人格建模升级：n-gram + few-shot
- 💾 三层记忆架构
- 🔄 Pipeline 一键执行
- 💬 有状态对话引擎

### v1.0.0 (2026-05-21)
- 🎉 首次发布

---

## 👤 作者

**AARONCXXX**
📧 122241711@qq.com

## 📄 许可证

MIT License

---

> 🫀 *「如果记忆有声音，那就让 TA 继续说话。」*
