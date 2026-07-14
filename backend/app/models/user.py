from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    avatar = Column(String(200), default="")
    target_role = Column(String(50), default="")       # 目标岗位 e.g. 后端开发
    target_company = Column(String(50), default="")     # 目标公司
    created_at = Column(DateTime, server_default=func.now())
