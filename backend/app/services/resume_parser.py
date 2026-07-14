'''
简历文件解析服务

支持 PDF (.pdf) 和 Word (.docx) 格式。
提取纯文本供 LLM 分析使用。
'''

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 支持的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_MB = 10


class ResumeParseError(Exception):
    '''简历解析异常'''
    pass


def extract_text_from_pdf(file_path: str) -> str:
    '''从 PDF 提取文本'''
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception as e:
        raise ResumeParseError(f"PDF 解析失败: {e}")


def extract_text_from_docx(file_path: str) -> str:
    '''从 DOCX 提取文本'''
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        raise ResumeParseError(f"DOCX 解析失败: {e}")


def validate_file(filename: str, file_size: int) -> None:
    '''校验上传文件'''
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ResumeParseError(
            f"不支持的文件格式 '{ext}'，仅支持 {', '.join(ALLOWED_EXTENSIONS)}"
        )

    size_mb = file_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ResumeParseError(
            f"文件过大 ({size_mb:.1f}MB)，最大支持 {MAX_FILE_SIZE_MB}MB"
        )


def parse_resume(file_path: str, original_filename: str) -> str:
    '''
    解析简历文件，返回纯文本。

    Args:
        file_path: 服务器上的文件路径
        original_filename: 原始文件名（用于判断格式）

    Returns:
        提取的纯文本

    Raises:
        ResumeParseError: 解析失败
    '''
    ext = Path(original_filename).suffix.lower()

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        text = extract_text_from_docx(file_path)
    else:
        raise ResumeParseError(f"不支持的文件格式: {ext}")

    if not text or not text.strip():
        raise ResumeParseError("未能从文件中提取到文本，文件可能为空或为扫描件")

    logger.info(
        "Resume parsed: %s, extracted %d chars",
        original_filename, len(text)
    )
    return text.strip()


def get_upload_path(filename: str) -> str:
    '''生成上传文件的存储路径'''
    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    # 加时间戳防止文件名冲突
    import time
    timestamp = int(time.time())
    safe_name = f"{timestamp}_{filename}"
    return str(upload_dir / safe_name)
