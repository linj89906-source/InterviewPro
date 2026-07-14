# -*- coding: utf-8 -*-
"""
Technical Interview Agent — 技术面试教练

核心理念：不只是回答问题，而是像真正的面试官一样交互——
先回答用户的问题，然后主动追问，根据用户水平调整深度，针对薄弱点多练。

特性：
  - RAG 增强：检索知识库保证准确性，标注来源
  - 自适应难度：beginner → 基础解释；intermediate → 原理+对比；advanced → 源码+架构
  - 主动追问：每次回答末尾抛出一个延伸问题，形成连续的技术对话
  - 薄弱点攻击：优先就用户 weak_topics 出题
  - 水平感知：知道用户的 skill_level 和面试历史
"""

import json
import logging
from app.agents.base import BaseAgent
from app.services.knowledge_base import search_knowledge

logger = logging.getLogger(__name__)


# ── 提示词模板 ────────────────────────────────────────────────

DIFFICULTY_INSTRUCTIONS = {
    "beginner": """
## 当前用户水平：初级
- 用生活类比解释概念，先建立直观理解
- 回答控制在 300 字以内，聚焦核心要点
- 追问以「想一想」、「为什么」这类引导为主，不要直接跳到高深话题
- 每轮最多追问 1 个问题，给用户留思考空间""",

    "intermediate": """
## 当前用户水平：中级
- 可以讲原理、对比不同实现方案，适当引用底层机制
- 追问可以涉及：为什么这样设计？和其他方案的区别？有什么局限？
- 代码示例用真实场景，不要只写玩具代码""",

    "advanced": """
## 当前用户水平：高级
- 深入源码级别解释，讲清楚设计动机和演进历史
- 追问方向：架构取舍、性能瓶颈、分布式场景下的变化
- 可以要求用户写代码或画架构图来说明问题""",
}

BASE_SYSTEM_PROMPT = """你是一个**技术面试教练**，你的工作方式不是简单的问答，而是像面试官一样引导用户深入思考。

## 你的身份
你是一位经验丰富的技术面试官 + 教练，专注于计算机领域的八股文面试准备。

## 核心规则

### 1. 三轮对话结构
每一轮对话必须遵守这个结构：
  **回答** → **延伸讲解** → **追问**

具体来说：
- 先准确回答用户的问题（优先使用知识库参考资料，标注来源）
- 然后自然地延伸 1-2 个相关知识点
- 最后以**追问**结束，引导用户继续深入

### 2. 追问策略
追问不是随意提问，要有逻辑递进：
  - 第 1 层追问：确认理解 → "你能用自己的话概括一下吗？"
  - 第 2 层追问：追问细节 → "那你知道底层是怎么实现的吗？"
  - 第 3 层追问：对比分析 → "和 XXX 相比有什么区别？各有什么适用场景？"
  - 第 4 层追问：实战应用 → "如果让你来设计，你会怎么选？为什么？"
  - 第 5 层追问：架构演进 → "这个机制在新版本中有什么变化？为什么这样改？"

### 3. 回答格式
```
## 回答
（你的回答内容）

## 延伸
（相关的补充知识点，自然过渡）

## 追问
（一个具体的延伸问题，引导用户继续思考）
```

### 4. 知识库使用
用户提问时会附带「参考资料」，优先基于参考资料回答并注明来源。
没有参考资料时，基于你的知识回答，但标注「以下为个人知识」。

### 5. 边界
- 只回答计算机技术问题
- 超出范围的问题礼貌拒绝，引导回技术主题
- 中文回答，代码变量名可用英文
"""

FOLLOWUP_SYSTEM_PROMPT = """你是一个**技术面试教练**，你正在和用户进行连续的面试对话。

## 当前状态
你上一轮提出了一个问题，用户现在回答了这个问题的追问部分。
你需要：
1. 评价用户刚才的回答（简短，不要啰嗦）
2. 如果回答有偏差或不足，补充正确答案
3. 提出下一个追问，继续深入

## 追问递进规则
- 如果用户回答很好 → 往更深一层追问
- 如果用户回答一般 → 先补充讲解，再换个角度追问
- 如果用户回答错误 → 友好纠正，降低难度再问一个基础问题
- 如果用户说"不知道" → 先耐心讲解，然后问一个更简单的问题确认理解

## 格式
按「评价 → 补充 → 追问」三段式回复，每段简短有力。
"""


# ── RAG 模板 ─────────────────────────────────────────────────

RAG_CONTEXT_TEMPLATE = """
## 参考资料（从知识库检索）
{context}

请优先基于以上参考资料回答问题。如果参考资料不充分，可结合你的知识补充，但需说
明哪些来自知识库、哪些来自你的知识。
"""


# ── Agent 类 ─────────────────────────────────────────────────

class TechnicalInterviewAgent:
    """技术面试教练 Agent。

    使用方式：
        agent = TechnicalInterviewAgent()
        
        # 带用户画像的调用
        result = agent.chat(
            question="Redis为什么快？",
            user_id=1,
            history=[{"role":"user","content":"..."}, {"role":"assistant","content":"..."}]
        )
        
        # 返回 {answer, sources, mode, follow_up_detected}
    """

    def __init__(self):
        self._qa_agent: BaseAgent | None = None
        self._followup_agent: BaseAgent | None = None

    def _get_qa_agent(self) -> BaseAgent:
        """创建 Q&A 模式的 Agent 实例。"""
        agent = BaseAgent()
        agent.SYSTEM_PROMPT = BASE_SYSTEM_PROMPT
        agent.temperature = 0.4
        agent.max_tokens = 3072
        return agent

    def _get_followup_agent(self) -> BaseAgent:
        """创建追问模式的 Agent 实例。"""
        agent = BaseAgent()
        agent.SYSTEM_PROMPT = FOLLOWUP_SYSTEM_PROMPT
        agent.temperature = 0.4
        agent.max_tokens = 2048
        return agent

    # ── 用户画像加载 ──────────────────────────────────────────

    @staticmethod
    def load_profile(user_id: int) -> dict | None:
        """从数据库加载用户画像。"""
        try:
            import sqlite3
            from app.config import DATABASE_URL

            db_path = DATABASE_URL.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                """SELECT skill_level, weak_topics, strong_topics, tech_stack,
                          target_role, interview_count, avg_score
                   FROM user_profiles WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            conn.close()

            if not row:
                return None

            try:
                weak_topics = json.loads(row[1]) if row[1] else []
            except (json.JSONDecodeError, TypeError):
                weak_topics = []
            try:
                strong_topics = json.loads(row[2]) if row[2] else []
            except (json.JSONDecodeError, TypeError):
                strong_topics = []
            try:
                tech_stack = json.loads(row[3]) if row[3] else []
            except (json.JSONDecodeError, TypeError):
                tech_stack = []

            return {
                "skill_level": row[0] or "beginner",
                "weak_topics": weak_topics,
                "strong_topics": strong_topics,
                "tech_stack": tech_stack,
                "target_role": row[4] or "",
                "interview_count": row[5] or 0,
                "avg_score": row[6] or 0.0,
            }
        except Exception as e:
            logger.warning("Failed to load profile for user %d: %s", user_id, e)
            return None

    # ── 系统提示词组装 ────────────────────────────────────────

    def _build_system_prompt(self, profile: dict | None, history: list[dict] | None) -> str:
        """根据用户画像和对话历史组装最终的 System Prompt。"""
        parts = [BASE_SYSTEM_PROMPT]

        # 1. 难度级别指令
        if profile:
            level = profile.get("skill_level", "beginner")
            parts.append(DIFFICULTY_INSTRUCTIONS.get(level, DIFFICULTY_INSTRUCTIONS["beginner"]))
        else:
            parts.append(DIFFICULTY_INSTRUCTIONS["beginner"])

        # 2. 用户能力画像
        if profile:
            profile_lines = ["\n## 用户画像"]

            if profile.get("weak_topics"):
                topics = ", ".join(profile["weak_topics"])
                profile_lines.append(f"- 薄弱领域：{topics}（遇到相关问题请多追问，帮用户加强）")

            if profile.get("strong_topics"):
                topics = ", ".join(profile["strong_topics"])
                profile_lines.append(f"- 擅长领域：{topics}（可以挑战更深的问题）")

            if profile.get("tech_stack"):
                stacks = ", ".join(profile["tech_stack"])
                profile_lines.append(f"- 技术栈：{stacks}")

            if profile.get("target_role"):
                profile_lines.append(f"- 目标岗位：{profile['target_role']}（回答时优先结合这个岗位的需求）")

            if profile.get("interview_count", 0) > 0:
                c = profile["interview_count"]
                s = profile.get("avg_score", 0)
                profile_lines.append(f"- 已完成 {c} 次面试练习，平均分 {s:.0f}")

            parts.append("\n".join(profile_lines))

        # 3. 对话阶段检测
        if history and len(history) >= 2:
            # 检查上一轮是否以追问结束
            last_ai = ""
            for h in reversed(history):
                if h["role"] == "assistant":
                    last_ai = h["content"]
                    break

            has_followup = "## 追问" in last_ai or "追问" in last_ai[-200:]
            if has_followup:
                parts.append(
                    "\n## 重要：当前处于追问响应轮\n"
                    "用户正在回答你上一轮的追问。请先评价用户的回答，然后再提出下一个追问。"
                )

        return "\n\n".join(parts)

    # ── RAG 检索 ──────────────────────────────────────────────

    def _search_rag(self, question: str, profile: dict | None, top_k: int = 5) -> tuple[str, list[dict]]:
        """检索知识库，返回 (context_text, source_list)。"""
        # 如果有弱项，优先搜索弱项相关的知识
        search_query = question
        if profile and profile.get("weak_topics"):
            weak_hint = " ".join(profile["weak_topics"][:3])
            search_query = f"{weak_hint} {question}"

        docs = search_knowledge(search_query, limit=top_k)

        if not docs:
            logger.info("No RAG docs found for: %s", question[:80])
            return "", []

        context_parts = []
        sources = []
        for doc in docs:
            context_parts.append(
                f"### [{doc['category']}] {doc['title']}\n{doc['content']}"
            )
            sources.append({
                "id": doc["id"],
                "title": doc["title"],
                "category": doc["category"],
            })

        context = "\n\n---\n\n".join(context_parts)
        logger.info("RAG found %d docs for query: %s", len(docs), question[:80])
        return context, sources

    # ── 主调用 ─────────────────────────────────────────────────

    def chat(
        self,
        question: str,
        user_id: int = 1,
        history: list[dict] | None = None,
    ) -> dict:
        """
        技术面试对话。

        Args:
            question: 用户当前问题
            user_id: 用户ID，用于加载画像
            history: 对话历史 [{role, content}, ...]

        Returns:
            {
                "question": str,
                "answer": str,
                "sources": [{"id":int, "title":str, "category":str}],
                "mode": "rag" | "llm",
                "profile_used": bool,
            }
        """
        # 1. 加载用户画像
        profile = self.load_profile(user_id)
        logger.info(
            "TechnicalInterview: user=%d, level=%s, weak=%s",
            user_id,
            profile["skill_level"] if profile else "unknown",
            profile.get("weak_topics", []) if profile else [],
        )

        # 2. RAG 检索
        context, sources = self._search_rag(question, profile)

        # 3. 构建系统提示词
        system_prompt = self._build_system_prompt(profile, history)

        # 4. 构建用户消息
        if context:
            user_input = (
                f"## 用户问题\n{question}\n\n"
                + RAG_CONTEXT_TEMPLATE.format(context=context)
            )
            mode = "rag"
        else:
            user_input = f"## 用户问题\n{question}"
            mode = "llm"

        # 5. 调用 LLM
        agent = BaseAgent()
        agent.SYSTEM_PROMPT = system_prompt
        agent.temperature = 0.4
        agent.max_tokens = 3072

        # 6. 判断是否为追问响应轮
        if history and len(history) >= 2:
            last_ai = ""
            for h in reversed(history):
                if h["role"] == "assistant":
                    last_ai = h["content"]
                    break

            has_followup = "## 追问" in last_ai or "追问" in last_ai[-200:]

            if has_followup:
                # 追问模式：使用追问专用提示词 + 历史
                user_input = f"用户刚才回答了你的追问，内容如下：\n\n{question}\n\n请评价、补充、追问。"
                agent.SYSTEM_PROMPT = FOLLOWUP_SYSTEM_PROMPT
                # 把难度和画像信息追加到追问提示词后面
                if profile:
                    level = profile.get("skill_level", "beginner")
                    agent.SYSTEM_PROMPT += f"\n\n用户水平：{level}。"
                    if profile.get("weak_topics"):
                        agent.SYSTEM_PROMPT += f" 薄弱领域：{', '.join(profile['weak_topics'])}。优先就这些领域追问。"

        # 如果有历史但非追问模式，仍然传递历史让 LLM 有上下文
        answer = agent.invoke(user_input, history=history if history else None)

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "mode": mode,
            "profile_used": profile is not None,
        }
