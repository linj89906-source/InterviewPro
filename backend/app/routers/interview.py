from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
from app.database import get_db
from app.models import InterviewSession, InterviewRecord, Question
from app.services.ai_interviewer import get_interview_response, evaluate_answer
from app.agents.interview_agent import InterviewAgent

router = APIRouter(prefix="/api/interview", tags=["interview"])

class StartInterviewRequest(BaseModel):
    user_id: int = 1
    role: str = "后端开发"
    company: str = ""
    mode: str = "practice"

class ChatRequest(BaseModel):
    session_id: int
    message: str
    history: list[dict] = []

class EvaluateRequest(BaseModel):
    question: str
    user_answer: str

@router.post("/start")
async def start_interview(req: StartInterviewRequest, db: Session = Depends(get_db)):
    session = InterviewSession(
        user_id=req.user_id,
        role=req.role,
        mode=req.mode
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    config = {"role": req.role, "company": req.company, "mode": req.mode}
    result = await get_interview_response(
        user_message="面试开始，请先做自我介绍并提出第一个问题",
        conversation_history=[],
        interview_config=config
    )
    return {"session_id": session.id, "message": result}

@router.post("/chat")
async def interview_chat(req: ChatRequest, db: Session = Depends(get_db)):
    session = db.query(InterviewSession).filter(InterviewSession.id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config = {"role": session.role, "company": "", "mode": session.mode}
    result = await get_interview_response(
        user_message=req.message,
        conversation_history=req.history,
        interview_config=config
    )

    record = InterviewRecord(
        session_id=req.session_id,
        question_text=result.get("content", ""),
        user_answer=req.message,
        ai_feedback=json.dumps(result.get("feedback_detail", {})),
        score=result.get("score", 0)
    )
    db.add(record)
    session.total_questions += 1
    db.commit()

    return {"message": result, "record_id": record.id}

@router.post("/evaluate")
async def evaluate(req: EvaluateRequest):
    result = await evaluate_answer(req.question, req.user_answer)
    return result

@router.get("/sessions/{user_id}")
async def get_sessions(user_id: int, db: Session = Depends(get_db)):
    sessions = db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id
    ).order_by(InterviewSession.created_at.desc()).all()
    return [{"id": s.id, "role": s.role, "mode": s.mode, "status": s.status,
             "total_questions": s.total_questions, "score_avg": s.score_avg,
             "created_at": s.created_at.isoformat() if s.created_at else None} for s in sessions]

@router.get("/records/{session_id}")
async def get_records(session_id: int, db: Session = Depends(get_db)):
    records = db.query(InterviewRecord).filter(
        InterviewRecord.session_id == session_id
    ).order_by(InterviewRecord.created_at.asc()).all()
    return [{"id": r.id, "question_text": r.question_text, "user_answer": r.user_answer,
             "ai_feedback": r.ai_feedback, "score": r.score, "round": r.round_number,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in records]

@router.post("/report/{session_id}")
async def generate_report(session_id: int, db: Session = Depends(get_db)):
    """生成面试会话的完整评估报告"""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    records = db.query(InterviewRecord).filter(
        InterviewRecord.session_id == session_id
    ).order_by(InterviewRecord.created_at.asc()).all()

    if not records:
        raise HTTPException(status_code=400, detail="该会话没有面试记录")

    # 构建记录列表
    record_list = [
        {
            "question_text": r.question_text,
            "user_answer": r.user_answer,
            "score": r.score,
            "ai_feedback": r.ai_feedback,
        }
        for r in records
    ]

    try:
        agent = InterviewAgent()
        report = agent.generate_report(record_list, role=session.role or "")

        # 更新 session 的状态和平均分
        if "overall_score" in report:
            session.score_avg = float(report["overall_score"])
        session.status = "completed"
        db.commit()

        return {
            "session_id": session_id,
            "role": session.role,
            "total_questions": session.total_questions,
            "report": report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)[:200]}")
