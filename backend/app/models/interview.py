from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from app.database import Base

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(30), default="")
    mode = Column(String(20), default="practice")     # practice / mock / quick
    status = Column(String(20), default="active")     # active / completed
    total_questions = Column(Integer, default=0)
    score_avg = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

class InterviewRecord(Base):
    __tablename__ = "interview_records"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    question_text = Column(Text, nullable=False)
    user_answer = Column(Text, default="")
    ai_feedback = Column(Text, default="")
    score = Column(Integer, default=0)                # 0-100
    round_number = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
