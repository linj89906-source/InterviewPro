# -*- coding: utf-8 -*-
"""
技术面试 API 路由

POST /api/knowledge/interview  — 技术面试教练（自适应难度 + 追问 + RAG）
POST /api/knowledge/chat       — 纯 LLM 技术问答（兼容旧版）
POST /api/knowledge/rag        — RAG 增强问答（兼容旧版）
GET  /api/knowledge/health     — 健康检查
GET  /api/knowledge/profile    — 查看用户画像
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.coding_agent import CodingAgent
from app.agents.technical_interview_agent import TechnicalInterviewAgent
from app.models.conversation import Conversation, Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

HISTORY_ROUNDS = 10


# ── 请求/响应模型 ──────────────────────────────────────────

class InterviewRequest(BaseModel):
    """技术面试对话请求"""
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题或答案")
    user_id: int = Field(default=1, description="用户ID")
    conversation_id: int | None = Field(default=None, description="对话ID，不传自动创建")


class InterviewResponse(BaseModel):
    """技术面试对话响应"""
    question: str
    answer: str
    sources: list[dict]
    mode: str                    # "rag" | "llm"
    profile_used: bool
    conversation_id: int
    skill_level: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    question: str
    answer: str


class RAGRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    category: str | None = Field(default=None)


class RAGResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict]
    mode: str


class ProfileResponse(BaseModel):
    user_id: int
    profile: dict | None


# ── 辅助函数 ────────────────────────────────────────────────

def _first_line(text: str, max_len: int = 40) -> str:
    line = text.strip().split("\n")[0]
    return line[:max_len] + ("..." if len(line) > max_len else "")


def _load_history(db: Session, conversation_id: int) -> list[dict]:
    """加载最近 N 轮对话历史。"""
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_ROUNDS * 2)
        .all()
    )
    msgs.reverse()
    return [{"role": m.role, "content": m.content} for m in msgs]


# ── 核心端点：技术面试教练 ──────────────────────────────────

@router.post("/interview", response_model=InterviewResponse)
async def technical_interview(req: InterviewRequest, db: Session = Depends(get_db)):
    """
    技术面试教练 —— 核心升级端点。

    特性：
    - 自适应难度（根据用户画像 beginner/intermediate/advanced）
    - 主动追问（每次回答末尾带延伸问题）
    - RAG 增强（检索知识库，标注来源）
    - 薄弱点攻击（优先提问用户 weak_topics）
    - 跨轮记忆（通过 conversation_id 传递对话上下文）

    使用流程：
    1. 用户提问/回答 → Agent 回复 + 追问
    2. 用户回答追问 → Agent 评价 + 补充 + 新追问
    3. 追问链自然递进，从表面到深层

    前端使用：把返回的 conversation_id 存下来，后续请求带上来保持对话连续性。
    """
    try:
        # 1. 拿到或创建对话
        if req.conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
            if not conv:
                raise HTTPException(status_code=404, detail="对话不存在")
        else:
            conv = Conversation(user_id=req.user_id, title=_first_line(req.question))
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # 2. 加载历史
        history = _load_history(db, conv.id)

        # 3. 保存用户消息
        user_msg = Message(conversation_id=conv.id, role="user", content=req.question)
        db.add(user_msg)
        db.commit()

        # 4. 调用 Technical Interview Agent
        agent = TechnicalInterviewAgent()
        result = agent.chat(
            question=req.question,
            user_id=req.user_id,
            history=history,
        )

        # 5. 保存 AI 回复
        ai_msg = Message(conversation_id=conv.id, role="assistant", content=result["answer"])
        db.add(ai_msg)
        db.commit()

        # 6. 获取当前画像水平
        profile = TechnicalInterviewAgent.load_profile(req.user_id)
        skill_level = profile["skill_level"] if profile else "beginner"

        return InterviewResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            mode=result["mode"],
            profile_used=result["profile_used"],
            conversation_id=conv.id,
            skill_level=skill_level,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Technical interview failed")
        raise HTTPException(status_code=500, detail=f"技术面试服务异常: {str(e)[:200]}")


# ── 兼容旧版端点 ────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """纯 LLM 技术问答（兼容旧版）。"""
    try:
        agent = KnowledgeAgent()
        answer = agent.chat(req.question)
        if not answer or not answer.strip():
            raise HTTPException(status_code=500, detail="AI 返回了空回答")
        return ChatResponse(question=req.question, answer=answer)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Knowledge chat failed")
        raise HTTPException(status_code=500, detail=f"问答服务异常: {str(e)[:200]}")


@router.post("/rag", response_model=RAGResponse)
async def rag_chat(req: RAGRequest):
    """RAG 增强问答（兼容旧版）。"""
    try:
        agent = CodingAgent()
        result = agent.chat(question=req.question, category=req.category)
        if not result.get("answer") or not result["answer"].strip():
            raise HTTPException(status_code=500, detail="AI 返回了空回答")
        return RAGResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            mode=result["mode"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("RAG chat failed")
        raise HTTPException(status_code=500, detail=f"RAG 问答异常: {str(e)[:200]}")


@router.get("/health")
async def health():
    return {"status": "ok", "service": "knowledge-agent"}


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user_id: int = Query(default=1)):
    """查看用户画像（调试用）。"""
    profile = TechnicalInterviewAgent.load_profile(user_id)
    return ProfileResponse(user_id=user_id, profile=profile)
