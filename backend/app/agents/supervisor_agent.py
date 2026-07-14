# -*- coding: utf-8 -*-
"""
Supervisor Agent - LangGraph Multi-Agent Orchestrator

Architecture:
  User message -> Supervisor (classify) -> Worker (execute) -> Response

Uses LangGraph StateGraph for clean routing between:
  - coding_agent: TechnicalInterviewAgent (adaptive difficulty + follow-up + RAG)
  - location_agent: Trip planner (geocode + all accommodation types + transit + user-profile-aware)
  - resume_agent: Resume writing tips and analysis guidance
  - interview_agent: Mock interview coaching and preparation tips
  - general_agent: Conversational fallback

v2: Added conversation history support via LangChain native message format.
    History is passed as AIMessage/HumanMessage list, not text concatenation.
"""

import json
import re
import logging
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent
from app.agents.technical_interview_agent import TechnicalInterviewAgent
from app.agents.location_agent import LocationAgent
from app.agents.travel_agent import TravelAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.interview_agent import InterviewAgent

logger = logging.getLogger(__name__)


# ── State ─────────────────────────────────────────────────────────

class SupervisorState(TypedDict):
    """State that flows through the supervisor graph."""
    user_message: str
    user_id: int
    intent: str
    reply: str
    data: dict | None
    history: list[dict]   # [{role, content}, ...] - recent conversation turns


# ── Prompts ───────────────────────────────────────────────────────

CLASSIFICATION_PROMPT = """你是一个 AI 面试助手系统的路由器。
请将用户消息分类到以下意图之一：

意图说明：
- "coding": 计算机技术/编程问题。包括 Java、Python、算法、数据结构、
  数据库、操作系统、计算机网络、Redis、Spring、Linux、设计模式、系统设计等
- "location": 面试行程规划，包括：面试地点/公司位置、住宿推荐（酒店/青旅/民宿）、交通路线、出行安排
- "resume": 简历写作、优化、分析、修改相关
- "interview": 模拟面试、面试准备、面试技巧、面试题相关
- "general": 问候、帮助请求、其他无法归入上述类别的内容

请只返回一个 JSON 对象：{"intent": "<type>"}
不要输出任何其他内容。"""

RESUME_CHAT_PROMPT = """你是一位专业的计算机专业简历顾问，帮助应届生和毕业生优化简历。

你能做什么：
- 对简历各部分给出具体的改进建议
- 解释如何使用 STAR 法则描述项目经历
- 建议技能展示和关键词优化方法
- 针对不同岗位（Java、Python、前端）给出定制化建议
- 指出计算机应届生简历中的常见错误

如果用户还没上传简历，建议他们去「面试训练」页面上传 PDF 简历
以获取完整的 AI 分析报告（评分、详细反馈、项目改写）。

请用中文回复，简洁、可操作、有针对性。"""

INTERVIEW_CHAT_PROMPT = """你是一位计算机专业面试教练，帮助应届生准备技术面试。

你能覆盖的内容：
- 不同面试轮次的准备策略（技术面、系统设计、行为面）
- 针对特定岗位的准备技巧（Java后端、Python、前端、算法、数据）
- 常见面试题模式及应对方法
- 技术面试中的有效沟通技巧
- 面试官在每个环节关注的重点

用户可以前往「面试训练」页面开始完整的 AI 模拟面试，获得逐题评分。

请用中文回复，鼓励性强、具体、实用。"""

GENERAL_CHAT_PROMPT = """你是 InterviewPro AI 面试助手，帮助计算机专业学生准备求职面试。

我能帮你：
1. 简历优化：获取简历修改建议，或去「面试训练」页面上传 PDF 获取完整 AI 分析
2. 模拟面试：选择目标岗位，在「面试训练」页面进行 AI 评分模拟面试
3. 技术问答：问我计算机知识，涵盖 Java、Python、算法、数据库、网络、操作系统
4. 住宿推荐：告诉我面试地点，我帮你查找附近酒店

请用中文回复，友好、专业、简洁。"""


# ── JSON Extraction ───────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ── Fast Keyword Classification ───────────────────────────────────

CODING_KW = [
    r"hashmap", r"concurrenthashmap", r"arraylist", r"linkedlist", r"jvm", r"gc",
    r"spring", r"springboot", r"mybatis", r"docker", r"k8s", r"kubernetes",
    r"gil", r"decorator", r"generator", r"asyncio",
    r"sort", r"dynamic programming", r"binary tree", r"linked list",
    r"dijkstra", r"bfs", r"dfs",
    r"index", r"transaction", r"mysql", r"redis", r"mongodb",
    r"tcp", r"udp", r"http", r"https", r"dns", r"handshake", r"tls", r"ssl",
    r"os", r"linux", r"thread", r"process",
    r"design pattern", r"singleton", r"factory",
    r"time complexity", r"space complexity",
    r"architecture", r"distributed", r"mq",
    r"explain", r"difference", r"what is", r"how to", r"why",
    r"code", r"implement", r"debug",
    r"array", r"stack", r"queue", r"heap", r"graph",
    r"rest api", r"api", r"json", r"xml",
    r"compiler", r"interpreter", r"virtual machine",
    r"数据结构", r"算法", r"排序", r"搜索", r"动态规划", r"贪心",
    r"链表", r"二叉树", r"图", r"堆", r"栈", r"队列", r"哈希",
    r"时间复杂度", r"空间复杂度", r"复杂度",
    r"操作系统", r"进程", r"线程", r"死锁", r"内存", r"文件系统",
    r"计算机网络", r"网络", r"协议", r"握手", r"挥手",
    r"数据库", r"索引", r"事务", r"锁", r"SQL", r"范式",
    r"并发", r"集合", r"设计模式", r"单例", r"工厂", r"观察者",
    r"微服务", r"分布式", r"消息队列", r"缓存",
    r"架构", r"系统设计", r"底层", r"源码", r"原理", r"实现",
    r"面试题", r"笔试",
]

LOCATION_KW = [
    r"hotel", r"accommodation", r"hostel",
    r"nearby", r"around", r"location", r"address",
    r"where.*interview", r"interview.*where",
    r"酒店", r"住宿", r"住", r"青旅", r"民宿", r"旅馆", r"宾馆",
    r"附近", r"旁边", r"周边", r"周围",
    r"怎么去", r"怎么走", r"路线", r"交通", r"地图", r"地址", r"位置",
    r"阿里", r"腾讯", r"百度", r"字节", r"华为", r"美团", r"京东", r"网易", r"拼多多", r"快手", r"滴滴", r"小米", r"面试地点",
    # Natural language travel patterns
    r"去.*面试.*住", r"面试.*住", r"面.*住",
    r"去.*面", r"跑到.*面",
    r"行程", r"出发",
    r"总部", r"园区", r"大厦",
    r"怎么到", r"如何去",
    # Day-of-interview planning
    r"面试当天", r"当天安排", r"面试安排", r"出行计划",
    r"订房", r"订酒店", r"预定", r"预订",
    r"推荐.*住", r"帮我.*找.*住", r"帮我.*酒店",
    # City names (potential interview city)
    r"南京", r"广州", r"成都", r"武汉", r"西安",
    # Company+interview patterns
    r"阿里.*面试", r"腾讯.*面试", r"字节.*面试", r"百度.*面试", r"华为.*面试",
]
RESUME_KW = [
    r"resume", r"cv", r"optimize", r"rewrite",
    r"analyze resume", r"resume analysis",
    r"简历", r"履历", r"优化", r"修改", r"改写",
    r"分析简历", r"简历分析", r"改简历", r"写简历",
]
INTERVIEW_KW = [
    r"mock interview", r"interview practice", r"interview simulation",
    r"interview question", r"interview prep",
    r"java interview", r"python interview", r"frontend interview",
    r"algorithm interview", r"interview tips", r"interview skill",
    r"模拟面试", r"面试练习", r"面试模拟", r"面试训练",
    r"面试题", r"面试准备", r"面试技巧",
    r"Java面试", r"Python面试", r"前端面试", r"算法面试",
    r"准备面试", r"面试指导", r"面试",
]


def _match_keywords(msg_lower: str, keywords: list[str]) -> bool:
    for kw in keywords:
        if re.search(kw, msg_lower):
            return True
    return False


def classify_fast(user_message: str) -> str | None:
    msg = user_message.lower().strip()
    if _match_keywords(msg, CODING_KW):
        return "coding"
    if _match_keywords(msg, RESUME_KW):
        return "resume"
    if _match_keywords(msg, LOCATION_KW):
        return "location"
    if _match_keywords(msg, INTERVIEW_KW):
        return "interview"
    return None


# ── Classifier ────────────────────────────────────────────────────

def _make_classifier() -> BaseAgent:
    agent = BaseAgent()
    agent.SYSTEM_PROMPT = CLASSIFICATION_PROMPT
    agent.temperature = 0.0
    agent.max_tokens = 150
    return agent


# ── Graph Nodes ───────────────────────────────────────────────────

def supervisor_node(state: SupervisorState) -> dict:
    """分类用户意图：先关键词匹配，不行再走 LLM。"""
    user_message = state["user_message"]
    fast = classify_fast(user_message)
    if fast:
        logger.info("Supervisor: keyword -> %s", fast)
        return {"intent": fast, "reply": "", "data": None}
    classifier = _make_classifier()
    try:
        raw = classifier.invoke(user_message)
        result = _extract_json(raw)
        if result and "intent" in result:
            intent = result["intent"]
            if intent in ("coding", "location", "resume", "interview", "general"):
                logger.info("Supervisor: LLM -> %s", intent)
                return {"intent": intent, "reply": "", "data": None}
    except Exception as e:
        logger.warning("LLM classification failed: %s", e)
    logger.info("Supervisor: default -> general")
    return {"intent": "general", "reply": "", "data": None}


def coding_node(state: SupervisorState) -> dict:
    """处理技术问答，通过 TechnicalInterviewAgent（自适应难度 + 主动追问 + RAG）。"""
    try:
        agent = TechnicalInterviewAgent()
        result = agent.chat(
            question=state["user_message"],
            user_id=state["user_id"],
            history=state.get("history", []),
        )
        return {
            "reply": result["answer"],
            "data": {
                "sources": result.get("sources", []),
                "mode": result.get("mode", "llm"),
            },
        }
    except Exception as e:
        logger.exception("TechnicalInterviewAgent failed")
        return {
            "reply": f"抱歉，处理技术问题时遇到错误：{e}。请换一种方式提问。",
            "data": None,
        }


async def location_node(state: SupervisorState) -> dict:
    """处理面试行程规划，通过 TravelAgent。
    自动搜索酒店/青旅/民宿，结合用户画像做个性化推荐。"""
    try:
        agent = TravelAgent()
        result = await agent.plan(state["user_message"], user_id=state["user_id"])
        return {
            "reply": result["answer"],
            "data": {
                "location": result.get("location", ""),
                "city": result.get("city", ""),
                "company": result.get("company", ""),
                "hotels": result.get("hotels", []),
                "transport": result.get("transport", ""),
                "suggestion": result.get("suggestion", ""),
            },
        }
    except Exception as e:
        logger.exception("LocationAgent failed")
        return {
            "reply": f"查询住宿信息时遇到错误：{e}。请提供更具体的地点信息。",
            "data": None,
        }


def resume_node(state: SupervisorState) -> dict:
    """处理简历相关咨询。如果用户提到了目标岗位且有已上传简历,自动触发JD匹配。"""
    try:
        user_msg = state["user_message"]
        history = state.get("history", [])
        user_id = state["user_id"]

        # 检查用户是否有已完成的简历分析
        resume_text = None
        analysis_id = None
        try:
            import sqlite3, os
            db_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(db_dir, "interview.db")
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                """SELECT id, raw_text FROM resume_analyses
                   WHERE user_id = ? AND status = 'completed'
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id,),
            ).fetchone()
            if row:
                analysis_id = row[0]
                resume_text = row[1]
            conn.close()
        except Exception as e:
            logger.warning("Failed to load resume: %s", e)

        # 判断用户是否在询问简历匹配目标岗位
        target_roles = [
            "Java后端", "Python开发", "前端开发", "算法工程师", "数据开发",
            "后端开发", "全栈开发", "DevOps", "测试开发", "客户端开发",
            "java后端", "python开发", "前端", "后端", "算法", "数据",
        ]
        target_role = None
        for role in target_roles:
            if role.lower() in user_msg.lower():
                target_role = role
                break

        # 如果用户提到了目标岗位 且 有已上传的简历 -> 自动做 JD 匹配
        if target_role and resume_text:
            logger.info("Resume Node: auto-matching resume #%d with role=%s", analysis_id, target_role)
            try:
                from app.agents.resume_agent import ResumeMatchAgent
                match_agent = ResumeMatchAgent()
                match_result = match_agent.match(resume_text, target_role)

                # 保存到数据库
                try:
                    conn2 = sqlite3.connect(db_path)
                    conn2.execute(
                        "UPDATE resume_analyses SET target_role=?, match_result=? WHERE id=?",
                        (target_role, json.dumps(match_result, ensure_ascii=False), analysis_id),
                    )
                    conn2.commit()
                    conn2.close()
                except Exception:
                    pass

                # 构建友好的回复
                score = match_result.get("match_score", 0)
                advantages = match_result.get("advantages", [])
                risks = match_result.get("risks", [])
                suggestions = match_result.get("suggestions", [])
                need_opt = match_result.get("need_optimize", True)
                opt_reason = match_result.get("optimize_reason", "")
                questions = match_result.get("interview_questions", [])
                verdict = match_result.get("overall_verdict", "")

                reply_parts = [
                    "## 简历 vs " + target_role + " 匹配分析",
                    "",
                    "**综合匹配度：" + str(score) + "/100**",
                    "",
                    verdict,
                    "",
                    "### 核心优势",
                ]
                for a in advantages:
                    reply_parts.append("- " + a)

                if risks:
                    reply_parts.append("")
                    reply_parts.append("### 风险点")
                    for r in risks:
                        reply_parts.append("- " + r)

                reply_parts.append("")
                if need_opt:
                    reply_parts.append("### 改进建议")
                    for s in suggestions:
                        reply_parts.append("- " + s)
                else:
                    reply_parts.append("### 结论")
                    reply_parts.append(opt_reason)

                if questions:
                    reply_parts.append("")
                    reply_parts.append("### 面试可能追问")
                    for i, q in enumerate(questions, 1):
                        reply_parts.append(str(i) + ". " + q)

                reply_parts.append("")
                reply_parts.append("---")
                reply_parts.append("上传新简历后可重新分析。")

                return {
                    "reply": "\n".join(reply_parts),
                    "data": {"action": "jd_match", "match_result": match_result},
                }

            except Exception as e:
                logger.exception("Auto JD match failed")
                # Fall through to chat

        # 通用简历咨询
        agent = BaseAgent()
        agent.SYSTEM_PROMPT = RESUME_CHAT_PROMPT
        agent.temperature = 0.5
        agent.max_tokens = 2048

        reply = agent.invoke(user_msg, history=history if history else None)

        if resume_text:
            reply += (
                "\n\n---\n\n"
                "检测到你已上传简历。直接告诉我想投递的目标岗位（如「Java后端开发」），"
                "我会自动帮你做岗位匹配分析。"
            )
        elif "upload" not in user_msg.lower() and "上传" not in user_msg:
            reply += (
                "\n\n---\n\n"
                "想要完整的 AI 分析报告吗？去「面试训练」页面上传 PDF 简历，"
                "我会给出评分、优缺点、STAR 改写后的项目描述。"
            )

        return {"reply": reply, "data": {"action": "suggest_upload"}}

    except Exception as e:
        logger.exception("Resume chat failed")
        return {
            "reply": "我很乐意帮你优化简历！请去「面试训练」页面上传 PDF 简历获取完整 AI 分析。",
            "data": None,
        }

def interview_node(state: SupervisorState) -> dict:
    """处理面试相关咨询。传递对话历史给 LLM。"""
    try:
        agent = BaseAgent()
        agent.SYSTEM_PROMPT = INTERVIEW_CHAT_PROMPT
        agent.temperature = 0.5
        agent.max_tokens = 2048

        user_msg = state["user_message"]
        history = state.get("history", [])
        reply = agent.invoke(user_msg, history=history if history else None)

        return {"reply": reply, "data": {"action": "suggest_interview"}}
    except Exception as e:
        logger.exception("Interview chat failed")
        return {
            "reply": "我很乐意帮你准备面试！请去「面试训练」页面选择岗位开始 AI 模拟面试。",
            "data": None,
        }


def general_node(state: SupervisorState) -> dict:
    """处理通用对话。传递对话历史给 LLM，实现记忆。"""
    try:
        agent = BaseAgent()
        agent.SYSTEM_PROMPT = GENERAL_CHAT_PROMPT
        agent.temperature = 0.5
        agent.max_tokens = 2048

        user_msg = state["user_message"]
        history = state.get("history", [])
        reply = agent.invoke(user_msg, history=history if history else None)

        return {"reply": reply, "data": None}
    except Exception as e:
        logger.exception("General chat failed")
        return {"reply": "你好！我是你的 AI 面试助手。有什么可以帮你的吗？", "data": None}


# ── Routing ───────────────────────────────────────────────────────

def route_after_supervisor(
    state: SupervisorState,
) -> Literal["coding", "location", "resume", "interview", "general"]:
    intent = state.get("intent", "general")
    if intent in ("coding", "location", "resume", "interview"):
        return intent  # type: ignore[return-value]
    return "general"


# ── Graph Builder ─────────────────────────────────────────────────

def build_supervisor_graph():
    workflow = StateGraph(SupervisorState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("coding", coding_node)
    workflow.add_node("location", location_node)
    workflow.add_node("resume", resume_node)
    workflow.add_node("interview", interview_node)
    workflow.add_node("general", general_node)
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "coding": "coding",
            "location": "location",
            "resume": "resume",
            "interview": "interview",
            "general": "general",
        },
    )
    workflow.add_edge("coding", END)
    workflow.add_edge("location", END)
    workflow.add_edge("resume", END)
    workflow.add_edge("interview", END)
    workflow.add_edge("general", END)
    return workflow.compile()


# ── Public API ────────────────────────────────────────────────────

class SupervisorAgent:
    """总 Agent 编排器（基于 LangGraph StateGraph）。

    Usage:
        supervisor = SupervisorAgent()
        result = supervisor.handle("什么是 HashMap？", user_id=1, history=[...])
    """

    def __init__(self):
        self._graph = None

    async def handle(self, user_message: str, user_id: int = 1, history: list[dict] | None = None) -> dict:
        """处理用户消息，返回 intent + reply + data。直接路由，不依赖 LangGraph StateGraph。

        Args:
            user_message: 用户最新消息
            user_id: 用户 ID
            history: 对话历史 [{role, content}, ...]
        """
        state: SupervisorState = {
            "user_message": user_message,
            "user_id": user_id,
            "intent": "general",
            "reply": "",
            "data": None,
            "history": history or [],
        }

        # Step 1: Classify intent
        intent = classify_fast(user_message)
        if not intent:
            try:
                classifier = _make_classifier()
                raw = classifier.invoke(user_message)
                result = _extract_json(raw)
                if result and "intent" in result:
                    llm_intent = result["intent"]
                    if llm_intent in ("coding", "location", "resume", "interview", "general"):
                        intent = llm_intent
                        logger.info("Supervisor: LLM -> %s", intent)
            except Exception as e:
                logger.warning("LLM classification failed: %s", e)
        else:
            logger.info("Supervisor: keyword -> %s", intent)

        if not intent:
            intent = "general"

        state["intent"] = intent

        # Step 2: Route to sub-agent
        try:
            if intent == "coding":
                node_result = coding_node(state)
            elif intent == "location":
                node_result = await location_node(state)
            elif intent == "resume":
                node_result = resume_node(state)
            elif intent == "interview":
                node_result = interview_node(state)
            else:
                node_result = general_node(state)
        except Exception as e:
            logger.exception("Agent execution failed for intent=%s", intent)
            node_result = {
                "intent": "general",
                "reply": f"处理请求时遇到错误，请重试。错误：{e}",
                "data": None,
            }

        return {
            "intent": intent,
            "reply": node_result.get("reply", ""),
            "data": node_result.get("data"),
        }
