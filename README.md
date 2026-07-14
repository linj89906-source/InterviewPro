# InterviewPro — AI 面试助手

面向计算机专业应届生的 **一站式 AI 求职辅助平台**，基于 **LangGraph 多 Agent 架构**，覆盖简历优化、模拟面试、技术问答、面试住宿推荐四大场景。

---

## 架构总览

`
用户界面 (React + Vite)
        │
        ▼
  FastAPI 统一入口
        │
        ▼
┌───────────────────────────────┐
│   LangGraph Supervisor Agent  │
│                               │
│   用户消息 → 意图分类 → 路由   │
│       │          │            │
│   关键词匹配   LLM兜底        │
└───────┬───────┬───────┬───────┘
        │       │       │
   ┌────▼──┐ ┌─▼──┐ ┌──▼────┐
   │Coding │ │Resume│ │Travel │
   │ Agent │ │Agent │ │ Agent │
   │       │ │      │ │       │
   │ RAG   │ │Struct│ │ Tool  │
   │ 增强  │ │Output│ │Calling│
   └───────┘ └──────┘ └───────┘
        │       │       │
        └───────┼───────┘
                ▼
        DeepSeek / OpenAI
`

核心技术：**LangGraph** 状态图编排 · **RAG** (SQLite FTS5) · **Tool Calling** (高德地图 API) · **Structured Output** (Pydantic)

---

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- DeepSeek API Key（或其他 OpenAI 兼容 API）

### 1. 启动后端

`ash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入 API Key
python scripts/seed_knowledge.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
`

### 2. 启动前端

`ash
cd frontend
npm install
npm run dev
`

访问 **http://localhost:5173**

---

## 功能模块

### AI 简历优化
上传 PDF/DOCX 简历 → 7 维度综合评分 → 优势/不足分析 → STAR 法则改写项目经历 → HR 第一印象模拟

### AI 模拟面试
选择岗位（Java/Python/前端/算法/数据）→ 三种模式（练习/模拟/快速）→ AI 面试官逐题评分 → 生成评估报告

### 技术问答 (RAG)
覆盖 Java、Python、算法、数据库、网络、OS、Redis、Spring、Linux → FTS5 全文检索 + LLM 生成

### 面试住宿推荐 (Tool Calling)
自然语言描述面试地点 → LLM 提取地址 → 高德地图 API 搜索 → 推荐酒店/青旅/民宿

---

## Agent 架构

| Agent | 职责 | 核心技术 |
|-------|------|----------|
| **Supervisor** | 意图分类、消息路由 | LangGraph StateGraph + 条件路由 |
| **Coding** | 技术问答（自适应难度+追问） | RAG (FTS5) + 用户画像 |
| **Resume** | 简历分析、JD 匹配 | Structured Output (Pydantic) |
| **Interview** | 面试准备咨询 | 状态机 + 结构化协议 |
| **Travel** | 行程规划、住宿推荐 | Tool Calling (高德地图 API) |

### 路由策略

`
用户输入 "Redis 为什么快？"
    │
    ▼
Supervisor 关键词匹配 → intent: coding
    │
    ▼
Coding Agent
    ├── FTS5 检索知识库
    ├── 查询用户画像
    ├── 组装 Prompt（含历史 + RAG）
    └── LLM 生成回答 + 主动追问
`

---

## 项目结构

`
interview-system/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph Agent 层（6 个 Agent）
│   │   ├── routers/         # FastAPI 路由（7 个模块）
│   │   ├── services/        # 业务服务（简历解析/面试引擎/地图/知识库）
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── main.py          # 应用入口
│   │   ├── config.py        # 环境变量配置
│   │   └── database.py      # 数据库连接
│   ├── scripts/             # 数据初始化脚本
│   └── requirements.txt
├── frontend/
│   ├── src/pages/           # 5 个页面组件
│   ├── vite.config.ts       # Vite 配置（含 dev proxy）
│   └── package.json
├── render.yaml              # Render 部署配置
├── vercel.json              # Vercel 部署配置
└── DEPLOY.md                # 部署指南
`

---

## 部署

### 后端 → Render

1. 推送代码到 GitHub
2. Render Dashboard → New → Blueprint
3. 自动检测 
ender.yaml，设置环境变量
4. 一键部署

### 前端 → Vercel

1. Vercel 导入 GitHub 仓库
2. 设置环境变量 VITE_API_URL = Render 后端地址
3. 自动部署

详见 [DEPLOY.md](./DEPLOY.md)

---

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| OPENAI_API_KEY | API Key (DeepSeek/OpenAI) | ✅ |
| OPENAI_BASE_URL | API 地址 | ✅ |
| OPENAI_MODEL | 模型名称 | ✅ |
| AMAP_API_KEY | 高德地图 Key | 可选 |
| ALLOWED_ORIGINS | CORS 白名单 | 可选 |
| VITE_API_URL | 前端 API 地址 | 生产必填 |

---

## License

MIT
