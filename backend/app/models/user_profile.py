# -*- coding: utf-8 -*-
"""用户画像表 — 长期记忆的核心载体"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from app.database import Base


class UserProfile(Base):
    """用户画像：存储跨会话的稳定用户特征"""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # 基本信息
    major = Column(String(50), default="")                # 专业
    grade = Column(String(20), default="")                # 年级（应届/大三/研二...）
    school = Column(String(100), default="")              # 学校

    # 技术能力
    tech_stack = Column(Text, default="[]")               # 技术栈 JSON ["Java","Spring"]
    skill_level = Column(String(20), default="beginner")  # 整体水平: beginner/intermediate/advanced
    strong_topics = Column(Text, default="[]")            # 擅长领域 JSON ["数据结构","MySQL"]
    weak_topics = Column(Text, default="[]")              # 薄弱领域 JSON ["算法","JVM"]

    # 求职目标
    target_role = Column(String(50), default="")          # 目标岗位 如"后端开发"
    target_company = Column(String(50), default="")       # 目标公司 如"字节跳动"
    target_city = Column(String(50), default="")          # 目标城市 如"杭州"

    # 历史统计
    interview_count = Column(Integer, default=0)          # 累计面试/练习次数
    avg_score = Column(Float, default=0.0)                # 历史平均分
    last_resume_id = Column(Integer, nullable=True)       # 最近一份简历分析ID
    learning_log = Column(Text, default="[]")             # 学习记录 JSON [{date,topic,result}]

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
