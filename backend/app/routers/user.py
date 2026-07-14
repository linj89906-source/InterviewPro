from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.database import get_db
from app.models import User, InterviewSession, InterviewRecord

router = APIRouter(prefix="/api/user", tags=["user"])

class UserCreate(BaseModel):
    username: str
    target_role: str = ""
    target_company: str = ""

@router.post("/register")
async def register(req: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username exists")
    user = User(username=req.username, target_role=req.target_role, target_company=req.target_company)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username}

@router.get("/{user_id}/stats")
async def user_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    total_sessions = db.query(InterviewSession).filter(InterviewSession.user_id == user_id).count()
    total_questions = db.query(InterviewRecord).join(InterviewSession).filter(
        InterviewSession.user_id == user_id
    ).count()

    avg_score = db.query(func.avg(InterviewRecord.score)).join(InterviewSession).filter(
        InterviewSession.user_id == user_id
    ).scalar() or 0

    return {
        "username": user.username,
        "target_role": user.target_role,
        "total_sessions": total_sessions,
        "total_questions": total_questions,
        "avg_score": round(float(avg_score), 1),
        "recent_sessions": []
    }