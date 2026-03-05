# Originsnap

> AI-powered reverse image source finder — 上传图片，追溯最初来源与原作者

![screenshot](https://raw.githubusercontent.com/Zlllo/originsnap/main/docs/screenshot.png)

## ✨ Features

- **多引擎聚合搜索**：并发查询 SauceNAO、IQDB、ASCII2D、trace.moe 四大反向搜索引擎
- **AI 智能分析**：用 LLM 综合所有结果，推断最可能的原始来源和作者
- **动漫截图识别**：自动识别番剧名、集数、时间戳（via trace.moe）
- **外部引擎跳转**：一键跳转 Google Lens、Yandex、TinEye 继续搜索
- **现代化 UI**：暗色玻璃拟态主题，支持拖拽 / 粘贴 / 点击上传

## 🚀 Quick Start

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（必填）和 SAUCENAO_API_KEY（可选）

# 启动
python -m uvicorn main:app --port 8000

# 打开浏览器访问 http://localhost:8000
```

## ⚙️ Configuration

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_API_KEY` | ✅ | LLM API Key（OpenAI 或兼容格式） |
| `LLM_BASE_URL` | ❌ | API 地址，默认 `https://api.openai.com/v1` |
| `LLM_MODEL` | ❌ | 模型名，默认 `gpt-4o-mini` |
| `SAUCENAO_API_KEY` | ❌ | [SauceNAO](https://saucenao.com/user.php) API Key，提升搜索额度 |

## 🏗️ Architecture

```
main.py              → FastAPI 入口，图片上传 + 聚合搜索 API
analyzer.py          → AI 分析模块（LLM 汇总 + 降级启发式）
engines/
├── saucenao.py      → SauceNAO API（Pixiv / DeviantArt / Twitter）
├── iqdb.py          → IQDB HTML 解析（各 booru 站）
├── ascii2d.py       → ASCII2D HTML 解析（Pixiv / Twitter 作者）
├── tracemoe.py      → trace.moe API（动漫截图识别）
└── links.py         → 外部搜索引擎跳转链接生成
static/
├── index.html       → 单页前端
├── style.css        → 暗色主题样式
└── app.js           → 交互逻辑
```

## 📄 License

MIT
