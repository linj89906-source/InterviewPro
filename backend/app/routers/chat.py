# -*- coding: utf-8 -*-
"""
统一聊天 API 路由

POST /api/chat — Supervisor Agent 入口，自动路由到子 Agent
支持 conversation_id 实现对话记忆：不传则自动创建，传则加载历史
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.conversation import Conversation, Message
from app.agents.supervisor_agent import SupervisorAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

HISTORY_ROUNDS = 10  # 注入 LLM 的最近对话轮数


# ── Request / Response ────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")
    user_id: int = Field(default=1, description="用户ID")
    conversation_id: int | None = Field(default=None, description="对话ID，不传则自动创建新对话")


class ChatSource(BaseModel):
    id: int
    title: str
    category: str


class ChatData(BaseModel):
    sources: list[ChatSource] | None = None
    mode: str | None = None
    location: dict | str | None = None
    action: str | None = None
    target: str | None = None
    hotels: list[dict] | None = None
    transport: str | None = None
    suggestion: str | None = None


class ChatResponse(BaseModel):
    intent: str
    reply: str
    data: ChatData | None = None
    conversation_id: int | None = None


# ── Helpers ───────────────────────────────────────────────────────

def _first_line(text: str, max_len: int = 40) -> str:
    """取消息第一行作为对话标题。"""
    line = text.strip().split("\n")[0]
    return line[:max_len] + ("..." if len(line) > max_len else "")


def _load_history(db: Session, conversation_id: int, rounds: int = HISTORY_ROUNDS) -> list[dict]:
    """加载最近 N 轮对话历史（返回时间正序的 [{role, content}, ...]）。"""
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(rounds * 2)  # user + assistant 各一条算一轮
        .all()
    )
    msgs.reverse()  # 转为时间正序
    return [{"role": m.role, "content": m.content} for m in msgs]


# ── Route ─────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    统一对话入口。

    Supervisor Agent 自动识别意图并路由到子 Agent：
    - 技术问题 → Coding Agent (RAG增强)
    - 地点住宿 → Location Agent (高德地图)
    - 简历相关 → Resume Agent
    - 面试相关 → Interview Agent
    - 其他 → 通用对话

    支持 conversation_id：不传自动创建新对话，传了则加载历史实现记忆。
    """
    try:
        # ── 1. 拿到或创建对话 ──
        if req.conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
            if not conv:
                raise HTTPException(status_code=404, detail="对话不存在")
        else:
            conv = Conversation(user_id=req.user_id, title=_first_line(req.message))
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # ── 2. 先加载历史（不包含当前消息）──
        history = _load_history(db, conv.id)

        # ── 3. 保存用户消息 ──
        user_msg = Message(conversation_id=conv.id, role="user", content=req.message)
        db.add(user_msg)
        db.commit()

        # ── 4. 调用 Supervisor Agent（历史 + 当前消息）──
        supervisor = SupervisorAgent()
        result = await supervisor.handle(req.message, req.user_id, history=history)
        logger.info('[CHAT DEBUG] handle result intent=%s, reply[:100]=%s', result.get('intent'), result.get('reply','')[:100])

        # ── 5. 保存 AI 回复 ──
        ai_msg = Message(conversation_id=conv.id, role="assistant", content=result["reply"])
        db.add(ai_msg)
        db.commit()

        # ── 6. 构建响应 ──
        raw_data = result.get("data") or {}
        data = ChatData(
            sources=[ChatSource(**s) for s in raw_data.get("sources", [])]
            if raw_data.get("sources") else None,
            mode=raw_data.get("mode"),
            location=raw_data.get("location"),
            action=raw_data.get("action"),
            target=raw_data.get("target"),
            hotels=raw_data.get("hotels"),
            transport=raw_data.get("transport"),
            suggestion=raw_data.get("suggestion"),
        )

        return ChatResponse(
            intent=result["intent"],
            reply=result["reply"],
            data=data,
            conversation_id=conv.id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supervisor chat failed")
        raise HTTPException(status_code=500, detail=f"对话服务异常: {str(e)[:200]}")
