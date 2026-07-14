# InterviewPro 部署指南

## 架构

`
用户浏览器
    │
    ├── 前端 (Vercel) ─── React + Vite 静态站点
    │
    └── 后端 (Render) ─── FastAPI + LangGraph Agent 系统
                              │
                              ├── DeepSeek API（AI 对话、面试、简历分析）
                              └── 高德地图 API（住宿推荐）
`

## 一、后端部署到 Render

### 1.1 准备工作

确保代码已推送到 GitHub 仓库。

### 1.2 在 Render 上部署

**方式一：BluePrint 自动部署（推荐）**

1. 打开 [Render Dashboard](https://dashboard.render.com)
2. 点击 **New** → **Blueprint**
3. 连接你的 GitHub 仓库
4. Render 自动检测 ender.yaml，配置好服务
5. 在环境变量页面填入真实值（见下方）
6. 点击 **Apply** 开始部署

**方式二：手动创建 Web Service**

1. 点击 **New** → **Web Service**
2. 连接 GitHub 仓库
3. 配置：
   - **Name**: interviewpro-api
   - **Root Directory**: ackend
   - **Runtime**: Python 3
   - **Build Command**: pip install -r requirements.txt
   - **Start Command**: uvicorn app.main:app --host 0.0.0.0 --port 

### 1.3 环境变量设置

在 Render 的 Environment 页面添加以下变量：

| 变量名 | 说明 | 示例值 |
|---|---|---|
| OPENAI_API_KEY | DeepSeek 或 OpenAI API Key | sk-xxxxxxxx |
| OPENAI_BASE_URL | API 地址 | https://api.deepseek.com/v1 |
| OPENAI_MODEL | 模型名称 | deepseek-chat |
| AMAP_API_KEY | 高德地图 Key（可选） | 高德开放平台获取 |
| ALLOWED_ORIGINS | 前端域名（上线后设置） | https://你的域名.vercel.app |

> DATABASE_URL 不用设置，默认用 SQLite。注意：免费 Render 实例的磁盘是临时的，重启后数据会丢失。

### 1.4 验证部署

部署成功后，访问 https://interviewpro-api.onrender.com/api/health 应返回：
`json
{"status": "healthy"}
`

### 1.5 免费实例注意事项

- Render 免费计划：15 分钟无请求后自动休眠
- 下次请求需 30-50 秒冷启动
- 每月 750 小时运行时间（够用）

---

## 二、前端部署到 Vercel

> 前端需要先修改 API 地址（将所有 fetch('/api/...') 改为 fetch('https://你的Render域名/api/...')），再部署。

### 2.1 部署步骤

1. 打开 [Vercel](https://vercel.com)
2. 导入 GitHub 仓库
3. 配置：
   - **Root Directory**: rontend
   - **Build Command**: 
pm run build
   - **Output Directory**: dist
4. 添加环境变量：
   - VITE_API_URL = https://interviewpro-api.onrender.com
5. 点击 **Deploy**

---

## 三、本地开发

`ash
# 1. 启动后端
cd backend
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入真实 Key
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. 启动前端（新终端）
cd frontend
npm install
npm run dev
`

前端 http://localhost:5173 自动代理 API 到 http://localhost:8000。

---

## 四、API Key 安全

- .env 已加入 .gitignore，不会被提交到 Git
- 部署到 Render 时，API Key 通过环境变量注入，不写入代码
- 定期检查 .gitignore 确保 .env 和 *.db 不被提交
