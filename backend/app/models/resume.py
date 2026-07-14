'''
简历分析相关数据模型
'''

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from app.database import Base


class ResumeAnalysis(Base):
    '''简历分析记录表'''

    __tablename__ = "resume_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)

    # 上传信息
    file_name = Column(String(200), default="")        # 原始文件名
    file_path = Column(String(500), default="")        # 服务器存储路径
    raw_text = Column(Text, default="")                # 解析出的纯文本

    # AI分析结果 (JSON string)
    basic_info = Column(Text, default="")              # 基本信息: 姓名/学历/学校等
    quality_score = Column(Float, default=0.0)         # 综合评分 0-100
    strengths = Column(Text, default="")               # 优势列表 JSON
    weaknesses = Column(Text, default="")              # 不足列表 JSON
    suggestions = Column(Text, default="")             # 修改建议 JSON
    optimized_projects = Column(Text, default="")      # 优化后的项目经历 JSON
    hr_feedback = Column(Text, default="")             # HR视角评价
    target_role = Column(String(200), default="")     # 目标岗位
    match_result = Column(Text, default="")           # 岗位匹配结果 JSON

    # 状态
    status = Column(String(20), default="pending")     # pending/parsing/analyzing/completed/failed
    error_message = Column(Text, default="")           # 错误信息

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
