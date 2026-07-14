'''
简历优化 API 路由

POST /api/resume/upload  - 上传简历文件并触发 AI 分析
GET  /api/resume/history/{user_id} - 获取用户的分析历史
GET  /api/resume/{analysis_id} - 获取单次分析详情
'''

import json
import os
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import PendingRollbackError
from app.database import get_db
from app.models import ResumeAnalysis
from app.services.resume_parser import (
    validate_file,
    parse_resume,
    get_upload_path,
    ResumeParseError,
)
from app.agents.resume_agent import ResumeAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["resume"])


def _safe_float(value, default=0.0):
    '''安全转换为 float，支持 dict 中的数值提取'''
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        # 如果 quality_score 被嵌套在 dict 里，取第一个数值
        for v in value.values():
            if isinstance(v, (int, float)):
                return float(v)
    return default


def _safe_json_dumps(value):
    '''安全 JSON 序列化，支持 dict/list/str'''
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    target_role: str = "",
    db: Session = Depends(get_db),
):
    '''
    上传简历文件并进行 AI 分析。

    流程：校验文件 → 保存 → 解析文本 → AI分析 → 存库 → 返回结果
    '''
    # 1. 校验文件
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择文件")

    content = await file.read()
    file_size = len(content)

    try:
        validate_file(file.filename, file_size)
    except ResumeParseError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. 保存文件
    upload_path = get_upload_path(file.filename)
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)
    with open(upload_path, "wb") as f:
        f.write(content)

    # 3. 创建数据库记录
    analysis = ResumeAnalysis(
        user_id=1,
        file_name=file.filename,
        file_path=upload_path,
        target_role=target_role or "",
        status="parsing",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # 4. 解析文件 → 提取文本
    try:
        raw_text = parse_resume(upload_path, file.filename)
        analysis.raw_text = raw_text
        analysis.status = "analyzing"
        db.commit()
    except ResumeParseError as e:
        analysis.status = "failed"
        analysis.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    # 5. AI 分析
    try:
        agent = ResumeAgent()
        result = agent.analyze(raw_text)
        logger.info("AI analysis result keys: %s", list(result.keys()) if result else "empty")

        # 6. 安全存库 - 使用 _safe_float 处理评分
        score_breakdown = result.get("score_breakdown", {})
        analysis.quality_score = _safe_float(result.get("quality_score", 0))

        analysis.basic_info = _safe_json_dumps(result.get("basic_info", {}))
        analysis.strengths = _safe_json_dumps(result.get("strengths", []))
        analysis.weaknesses = _safe_json_dumps(result.get("weaknesses", []))
        analysis.suggestions = _safe_json_dumps(result.get("suggestions", []))
        analysis.optimized_projects = _safe_json_dumps(result.get("optimized_projects", []))

        hr_feedback = {
            "first_impression": result.get("hr_first_impression", ""),
            "overall_assessment": result.get("overall_assessment", ""),
            "score_breakdown": score_breakdown,
        }
        analysis.hr_feedback = _safe_json_dumps(hr_feedback)
        analysis.status = "completed"

        # If target_role provided, do JD matching
        match_result = None
        if target_role:
            try:
                from app.agents.resume_agent import ResumeMatchAgent
                match_agent = ResumeMatchAgent()
                match_result = match_agent.match(raw_text, target_role)
                analysis.match_result = _safe_json_dumps(match_result)
                logger.info("JD match completed for role: %s, score: %s",
                            target_role, match_result.get("match_score", 0))
            except Exception as match_err:
                logger.warning("JD match failed (non-fatal): %s", match_err)

        db.commit()
        db.refresh(analysis)

        return {
            "id": analysis.id,
            "status": analysis.status,
            "file_name": analysis.file_name,
            "target_role": target_role or "",
            "result": result,
            "match_result": match_result,
        }

    except HTTPException:
        raise
    except PendingRollbackError:
        try:
            db.rollback()
        except Exception:
            pass
        try:
            analysis.status = "failed"
            analysis.error_message = "数据库写入冲突，请重试"
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="数据库写入失败，请重试")
    except Exception as e:
        logger.exception("Resume analysis failed")
        try:
            db.rollback()
        except Exception:
            pass
        try:
            analysis.status = "failed"
            analysis.error_message = str(e)[:500]
            db.commit()
        except Exception as commit_err:
            logger.warning("Failed to save error status to DB: %s", commit_err)
        raise HTTPException(status_code=500, detail=f"AI 分析失败: {str(e)[:200]}")


@router.get("/history/{user_id}")
async def get_history(user_id: int, db: Session = Depends(get_db)):
    '''获取用户简历分析历史'''
    analyses = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == user_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": a.id,
            "file_name": a.file_name,
            "quality_score": a.quality_score,
            "status": a.status,
            "basic_info": _safe_json(a.basic_info),
            "hr_feedback": _safe_json(a.hr_feedback),
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in analyses
    ]


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    '''获取单次简历分析详情'''
    a = db.query(ResumeAnalysis).filter(ResumeAnalysis.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="分析记录不存在")

    return {
        "id": a.id,
        "file_name": a.file_name,
        "status": a.status,
        "quality_score": a.quality_score,
        "basic_info": _safe_json(a.basic_info),
        "strengths": _safe_json(a.strengths),
        "weaknesses": _safe_json(a.weaknesses),
        "suggestions": _safe_json(a.suggestions),
        "optimized_projects": _safe_json(a.optimized_projects),
        "hr_feedback": _safe_json(a.hr_feedback),
        "error_message": a.error_message,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _safe_json(value: str):
    '''安全解析 JSON 字符串'''
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


@router.post("/match")
async def match_resume_with_jd(
    analysis_id: int = 0,
    target_role: str = "",
    db: Session = Depends(get_db),
):
    """将已有的简历分析结果与目标岗位进行匹配。

    Args:
        analysis_id: 简历分析记录ID
        target_role: 目标岗位，如 "Java后端开发"

    Returns:
        JDMatchResult 字典
    """
    if not target_role:
        raise HTTPException(status_code=400, detail="请提供目标岗位 target_role")

    a = db.query(ResumeAnalysis).filter(ResumeAnalysis.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    if a.status != "completed":
        raise HTTPException(status_code=400, detail="简历尚未完成分析，请等待分析完成")
    if not a.raw_text:
        raise HTTPException(status_code=400, detail="简历文本为空")

    try:
        from app.agents.resume_agent import ResumeMatchAgent

        # Update target_role
        a.target_role = target_role

        # Run match
        match_agent = ResumeMatchAgent()
        match_result = match_agent.match(a.raw_text, target_role)
        a.match_result = _safe_json_dumps(match_result)
        db.commit()

        return {
            "analysis_id": analysis_id,
            "target_role": target_role,
            "match_result": match_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Resume JD match failed")
        raise HTTPException(status_code=500, detail=f"岗位匹配失败: {str(e)[:200]}")
