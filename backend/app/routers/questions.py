from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Question

router = APIRouter(prefix="/api/questions", tags=["questions"])

CATEGORIES = [
    "操作系统", "计算机网络", "数据库", "数据结构", "算法",
    "Java", "Python", "C++", "Go", "设计模式", "系统设计",
    "Linux", "分布式", "并发编程", "前端", "DevOps"
]

@router.get("/categories")
async def get_categories():
    return CATEGORIES

@router.get("")
async def list_questions(
    category: str = Query(None),
    difficulty: str = Query(None),
    role: str = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, le=50),
    db: Session = Depends(get_db)
):
    q = db.query(Question)
    if category:
        q = q.filter(Question.category == category)
    if difficulty:
        q = q.filter(Question.difficulty == difficulty)
    if role:
        q = q.filter(Question.role == role)
    total = q.count()
    questions = q.offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "items": [{"id": qu.id, "category": qu.category, "difficulty": qu.difficulty,
                    "role": qu.role, "company": qu.company, "title": qu.title,
                    "content": qu.content, "answer": qu.answer, "tags": qu.tags} for qu in questions]
    }

@router.get("/random")
async def random_question(
    category: str = Query(None),
    difficulty: str = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Question)
    if category:
        q = q.filter(Question.category == category)
    if difficulty:
        q = q.filter(Question.difficulty == difficulty)
    question = q.order_by(func.random()).first()
    if not question:
        return {"question": None, "message": "题库暂无匹配题目"}
    return {"question": {
        "id": question.id, "category": question.category, "difficulty": question.difficulty,
        "role": question.role, "title": question.title, "content": question.content,
        "answer": question.answer, "tags": question.tags
    }}
