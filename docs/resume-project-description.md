# 简历项目描述 — AI 面试助手 (InterviewPro)

> 以下内容可直接放入简历的项目经历部分。根据简历篇幅选择「完整版」或「精简版」。

---

## 精简版（适合 4-5 行简历空间）

**AI 面试助手 — 基于 LangGraph 的 Multi-Agent 应用** | 全栈开发 & AI 工程化

- 设计并实现基于 **LangGraph StateGraph** 的 Multi-Agent 编排系统，包含 Supervisor 路由 Agent 和 4 个领域子 Agent（简历分析、模拟面试、技术问答、住宿推荐），通过关键词匹配 + LLM 后备实现零成本意图分类
- 实现 **RAG 检索增强生成**：基于 SQLite FTS5 全文检索引擎构建计算机知识库，覆盖 Java/Python/算法/数据库等 10+ 领域，结合 DeepSeek LLM 实现技术问答
- 集成 **Tool Calling** 模式：LLM 提取面试地点参数后调用高德地图 API 进行 POI 周边搜索，实现住宿推荐功能
- 使用 **LangChain with_structured_output + Pydantic** 实现简历多维度评分（7 维度的结构化 JSON 输出），保障 AI 输出的格式可靠性
- 技术栈：Python (FastAPI) + React (TypeScript) + LangChain/LangGraph + SQLite + Docker

---

## 完整版（适合面试详细讲解）

### 项目名称

**InterviewPro — 基于 LangGraph 的 AI 面试助手**

### 项目描述

面向计算机专业应届生的一站式 AI 求职辅助平台，覆盖简历优化、模拟面试、技术问答、面试住宿推荐四大场景。核心亮点在于 **Multi-Agent 架构设计** 和 **AI 应用工程化落地**。

### 个人职责

**1. Multi-Agent 编排系统设计**

- 基于 **LangGraph StateGraph** 设计 Supervisor + Worker 多 Agent 架构
- Supervisor 节点通过中英双语关键词正则进行零成本意图分类，命中率 90%+，未命中时自动降级到 LLM 分类
- 实现条件路由（conditional edges）将用户消息分发到 Coding/Resume/Interview/Location 四个子 Agent
- 每个子 Agent 独立管理自己的 System Prompt、温度参数和输出 Schema

**2. RAG 检索增强生成**

- 构建计算机专业知识库，覆盖 Java、Python、算法、数据库、网络、操作系统等 10+ 技术领域
- 使用 SQLite FTS5 实现全文检索，通过数据库触发器自动维护索引同步
- 实现中文分词兼容处理，将 FTS5 特殊字符安全转义
- RAG 模式下将检索到的文档作为上下文注入 System Prompt，并提供参考来源追溯

**3. Tool Calling 落地实践**

- Location Agent 采用 LLM + API 协作模式：LLM 提取地点参数 → 调用高德地图 API 进行地理编码和 POI 搜索 → LLM 格式化推荐结果
- 设计三层容错机制：LLM JSON 提取 → 正则后备 → 原始输入直接搜索

**4. 结构化输出工程化**

- 简历分析维度使用 LangChain with_structured_output 绑定 Pydantic Schema
- 设计了评分维度分解、STAR 法则项目改写、HR 印象模拟等 7 个嵌套结构化字段
- 实现了三层 JSON 提取兜底：structured output → raw text 提取 → 加提示重试

**5. 其他工程实践**

- FastAPI 统一 API 网关，支持 CORS、文件上传（PDF/DOCX 解析）
- 前端 React + TypeScript + Vite，多页面 SPA 架构
- 面试模块实现状态机驱动的对话流程，支持练习/模拟/快速三种模式

### 技术栈

Python, FastAPI, LangChain, LangGraph, React, TypeScript, SQLite, DeepSeek API, 高德地图 API, FTS5

### 项目亮点

- 掌握 LangGraph 多 Agent 编排的工业级落地方式
- 理解 RAG 架构中检索质量、上下文注入、容错机制的关键设计
- 实践了 Tool Calling 中 LLM 决策与 API 执行的协作模式
- 深入理解 AI 应用中结构化输出的必要性和实现方案
