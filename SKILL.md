---
name: cyber-ex-resurrection
displayName: V1.2复活吧我的赛博爱人
description: 复活吧我的赛博前任 — 导入聊天截图+语音样本，克隆前任的语言风格和声音，通过IM机器人「复活」TA。含伦理合规、一键数据销毁、多引擎OCR、智能清洗。
metadata:
  openclaw:
    version: 1.2.1
  author: aaroncxxx
  tags: [voice-cloning, ocr, chatbot, wechat, resurrection, ethics, data-cleaning, rag, emotion, multi-dimensional-persona]
---

# 复活吧我的赛博前任 🫀

> 导入聊天截图 + 语音文件 → 克隆前任的人格与声音 → 通过微信/QQ/飞书/WhatsApp 复活 TA

## ⚖️ 伦理与法律声明

**本工具严禁用于以下用途：**
- 🚫 未经授权克隆他人人格
- 🚫 冒充他人进行欺诈、骚扰或诈骗
- 🚫 制作深度伪造内容（Deepfake）
- 🚫 侵犯他人隐私权、肖像权、名誉权

**使用前必须确认：**
- ✅ 已获得被克隆人的明确书面同意（或已故且获家属同意）
- ✅ 仅用于合法、正当、必要的目的
- ✅ 已阅读并理解相关法律法规

运行 `python3 main.py consent` 查看完整伦理声明和法律条文参考。

## 功能

1. **截图 OCR** — 多引擎（MIMO Omni / PaddleOCR / EasyOCR），支持表情包、手写体
2. **多格式导入** — txt / csv / html / 微信导出 / 手机备份
3. **智能清洗** — 自动过滤系统消息、广告、重复内容、无效对话
4. **对话重建** — 多张截图合并为结构化聊天记录
5. **人格建模** — 从聊天记录提取语言风格、口头禅、性格
6. **声音克隆** — OpenVoice v2（CPU）/ GPT-SoVITS（GPU）双引擎
7. **IM 机器人** — 微信（Wechaty）/ QQ / 飞书 / WhatsApp
8. **一键销毁** — 安全删除所有本地数据（覆写+删除）
9. **伦理合规** — 强制同意确认 + 法律风险提示

## 快速开始

```bash
cd skills/cyber-ex-resurrection

# 0. 伦理确认（首次使用必须）
python3 main.py consent

# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 GUI（推荐）
./start.sh              # macOS/Linux
start.bat               # Windows
python3 gui_app.py      # 直接启动

# 3. 或使用命令行
python3 main.py ocr --input data/screenshots/
python3 main.py import --input data/wechat.txt
python3 main.py clean
python3 main.py persona
python3 main.py voice --input data/voices/
python3 main.py bot --platform wechat

# 4. 一键部署（CLI）
python3 deploy.py --input data/screenshots/ --voices data/voices/ --platform wechat

# 5. 一键销毁（需要时）
python3 main.py destroy
```

## 命令

| 命令 | 说明 |
|------|------|
| `python3 gui_app.py` | 启动图形界面（推荐） |
| `python3 deploy.py` | 命令行一键部署 |
| `python3 main.py consent` | 查看/确认伦理声明，`--show-legal` 显示法律条文 |
| `python3 main.py ocr` | 截图 OCR 提取，`--engine` 选择引擎 |
| `python3 main.py import` | 导入聊天记录（txt/csv/html/备份） |
| `python3 main.py clean` | 智能数据清洗 |
| `python3 main.py persona` | 构建人格 |
| `python3 main.py voice` | 声音克隆 |
| `python3 main.py chat` | CLI 交互聊天 |
| `python3 main.py bot` | 启动 IM 机器人 |
| `python3 main.py pipeline` | 完整管线（导入→清洗→人格→声音→IM） |
| `python3 main.py destroy` | 一键数据销毁，`--scan` 仅扫描 |
| `python3 main.py info` | 查看配置和状态 |
| `./start.sh` / `start.bat` | 一键启动 GUI |

## OCR 引擎选择

| 引擎 | 适用场景 | 依赖 |
|------|---------|------|
| `mimo_omni` | 复杂截图、语义理解 | MIMO API |
| `paddleocr` | 手写体、竖排文字、特殊符号 | `pip install paddleocr` |
| `easyocr` | 多语言、表情包 | `pip install easyocr` |
| `multi` | 三引擎融合投票 | 以上全部 |

```bash
python3 main.py ocr --input data/screenshots/ --engine paddleocr
python3 main.py ocr --input data/screenshots/ --engine multi
```

## 导入格式

| 格式 | 说明 |
|------|------|
| JSON | 通用结构化数据 |
| CSV | 带标题行自动映射字段 |
| HTML | 微信导出的网页格式 |
| TXT (带时间戳) | `[2024-01-15 14:30] 我: 消息` |
| TXT (微信导出) | 带分隔线的导出格式 |
| SQLite/备份 | 手机备份数据库 |

```bash
python3 main.py import --input data/wechat.txt
python3 main.py import --input data/chat.csv
python3 main.py import --input data/backup.db
python3 main.py import --input data/chats/   # 导入整个目录
```

## 数据清洗

自动过滤：
- 系统消息（撤回、加群、拍一拍、通话记录等）
- 广告/推广内容
- 重复消息（基于相似度）
- 无效内容（纯表情、纯标点）
- 合并连续同角色短消息（5分钟内）

```bash
python3 main.py clean
python3 main.py clean --no-ads    # 保留广告
python3 main.py clean --keep-emoji-only  # 保留纯表情
```

## 一键数据销毁

```bash
python3 main.py destroy --scan    # 扫描本地数据
python3 main.py destroy           # 确认后安全销毁
python3 main.py destroy --target data/screenshots/  # 选择性销毁
```

安全销毁流程：文件覆写（零填充）→ 删除，确保不可恢复。

## 配置

编辑 `config.json` 配置 API Key、机器人参数等。

## 引擎选择

- **无 GPU / 轻量**: OpenVoice v2（零样本，5 秒音频）
- **有 GPU / 高质量**: GPT-SoVITS（1 分钟素材，中文最佳）

## 作者

- **AARONCXXX**
- 📧 122241711@qq.com

## 许可证

MIT License
