from sqlalchemy import Column, Integer, String, Text, Enum as SqlEnum
import enum
from app.database import Base

class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class QuestionCategory(str, enum.Enum):
    OS = "操作系统"
    NETWORK = "计算机网络"
    DATABASE = "数据库"
    DATASTRUCT = "数据结构"
    ALGORITHM = "算法"
    JAVA = "Java"
    PYTHON = "Python"
    CPP = "C++"
    GO = "Go"
    DESIGN_PATTERN = "设计模式"
    SYSTEM_DESIGN = "系统设计"
    LINUX = "Linux"
    DISTRIBUTED = "分布式"
    CONCURRENCY = "并发编程"
    FRONTEND = "前端"
    DEVOPS = "DevOps"

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(30), nullable=False, index=True)
    difficulty = Column(String(10), nullable=False, default="medium")
    role = Column(String(30), default="")            # 岗位: 后端/前端/算法/测试
    company = Column(String(30), default="")          # 来源公司
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    answer = Column(Text, default="")
    tags = Column(String(200), default="")            # comma-separated
    follow_up_hints = Column(Text, default="")        # 追问提示JSON
