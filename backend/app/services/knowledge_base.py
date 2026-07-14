'''
知识库文档模型 + FTS5 全文检索

使用 SQLite FTS5 实现轻量级语义检索，零外部依赖。
'''

import sqlite3
import re
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database import Base, engine, DATABASE_URL


class KnowledgeDoc(Base):
    '''知识库文档'''

    __tablename__ = "knowledge_docs"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(30), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())


def init_fts():
    '''初始化 FTS5 全文索引表'''
    db_path = DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
            title,
            content,
            category,
            content='knowledge_docs',
            content_rowid='id'
        )
    """)
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge_docs BEGIN
            INSERT INTO knowledge_fts(rowid, title, content, category)
            VALUES (new.id, new.title, new.content, new.category);
        END;
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge_docs BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, category)
            VALUES ('delete', old.id, old.title, old.content, old.category);
        END;
        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge_docs BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, category)
            VALUES ('delete', old.id, old.title, old.content, old.category);
            INSERT INTO knowledge_fts(rowid, title, content, category)
            VALUES (new.id, new.title, new.content, new.category);
        END;
    """)
    conn.commit()
    conn.close()


def _sanitize_fts5_query(query: str) -> str:
    '''
    将用户输入转成 FTS5 安全的查询字符串。

    FTS5 特殊字符需要处理：引号、括号、AND/OR/NOT、*、NEAR 等。
    简单策略：提取中文词和英文词，用 OR 连接做宽泛匹配。
    '''
    # 去掉 FTS5 特殊字符，保留中文、英文、数字、空格
    cleaned = re.sub(r'[^\w\u4e00-\u9fff\s]', ' ', query)
    # 分词：英文按空格，中文保留连续
    words = cleaned.split()
    if not words:
        return '""'
    # FTS5 每个词用双引号包裹防止语法错误，用 OR 连接
    safe_words = []
    for w in words:
        # 去掉词内的引号
        w = w.replace('"', '').replace("'", '')
        if w.strip():
            safe_words.append(f'"{w}"')
    if not safe_words:
        return '""'
    return ' OR '.join(safe_words)


def search_knowledge(query: str, limit: int = 5) -> list[dict]:
    '''FTS5 全文搜索，返回匹配的文档列表。'''
    db_path = DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)

    fts_query = _sanitize_fts5_query(query)

    sql = f"""
        SELECT k.id, k.title, k.content, k.category, k.source
        FROM knowledge_fts f
        JOIN knowledge_docs k ON f.rowid = k.id
        WHERE knowledge_fts MATCH '{fts_query}'
        ORDER BY rank
        LIMIT ?
    """

    try:
        rows = conn.execute(sql, (limit,)).fetchall()
    except sqlite3.OperationalError as e:
        # 如果 FTS5 查询仍有语法问题，回退到 LIKE 搜索
        like_pattern = f"%{query[:50]}%"
        rows = conn.execute(
            """
            SELECT k.id, k.title, k.content, k.category, k.source
            FROM knowledge_docs k
            WHERE k.title LIKE ? OR k.content LIKE ?
            ORDER BY k.id DESC
            LIMIT ?
            """,
            (like_pattern, like_pattern, limit),
        ).fetchall()

    conn.close()
    return [
        {
            "id": r[0],
            "title": r[1],
            "content": r[2],
            "category": r[3],
            "source": r[4],
        }
        for r in rows
    ]