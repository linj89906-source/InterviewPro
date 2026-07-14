'''
Coding Agent — RAG 增强代码知识问答

使用 SQLite FTS5 全文检索知识库，检索相关文档后
拼入 System Prompt 交给 LLM 生成答案。
'''

import logging
from app.agents.base import BaseAgent
from app.services.knowledge_base import search_knowledge

logger = logging.getLogger(__name__)

CODING_SYSTEM_PROMPT = '''你是一位资深的计算机技术专家和编程导师，专注于帮助计算机专业学生准备技术面试。

## 你的能力范围
你精通以下领域：
- Java：JVM、集合框架、并发编程、Spring、设计模式
- Python：GIL、装饰器、生成器、异步编程、Django/Flask
- 算法：排序、搜索、动态规划、贪心、回溯、分治、图算法
- 数据库：MySQL索引、事务、锁、SQL优化、范式设计、NoSQL
- 网络：TCP/IP、HTTP/HTTPS、DNS、Socket编程、OSI模型

## 知识库使用规则
用户提问时会附带「参考资料」，这些是从知识库中检索到的相关文档。
请优先基于参考资料回答问题，引用时注明来源。
如果参考资料不足以回答问题，可以结合你的知识补充，但需说明哪些来自知识库、哪些来自你的知识。

## 回答格式
1. **核心答案**：先给出简洁直接的结论
2. **详细解释**：展开说明原理和细节
3. **代码示例**：涉及编程的给出可运行代码
4. **面试提示**：如果常见面试题，标注考察点和加分回答
5. **参考来源**：列出使用的知识库文档标题

## 边界
- 只回答计算机技术问题
- 超出范围的问题礼貌拒绝
- 回答使用中文，代码变量名和注释可用英文
'''

RAG_USER_PROMPT_TEMPLATE = '''## 用户问题
{question}

## 参考资料（从知识库检索）
{context}

请基于以上参考资料回答问题。如果参考资料不充分，可结合你的知识补充。'''


class CodingAgent(BaseAgent):
    '''RAG 增强的编程知识问答 Agent'''

    SYSTEM_PROMPT = CODING_SYSTEM_PROMPT
    temperature = 0.3
    max_tokens = 3072

    def chat(self, question: str, category: str | None = None, top_k: int = 5) -> dict:
        '''
        RAG 问答：检索知识库 → 增强生成。

        Returns:
            {
                "question": str,
                "answer": str,
                "sources": [{"id": int, "title": str, "category": str}],
                "mode": "rag" | "llm"
            }
        '''
        # 1. 检索知识库
        # 如果指定了分类，在 query 中加入分类提示
        search_query = question
        if category:
            search_query = f"{category} {question}"

        docs = search_knowledge(search_query, limit=top_k)
        logger.info("CodingAgent RAG search: query=%r, found=%d docs", search_query, len(docs))

        # 2. 构建回答
        if docs:
            # 有检索结果 → RAG 模式
            context_parts = []
            sources = []
            for doc in docs:
                context_parts.append(
                    f"### [{doc['category']}] {doc['title']}\n{doc['content']}"
                )
                sources.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "category": doc["category"],
                })

            context = "\n\n---\n\n".join(context_parts)
            user_input = RAG_USER_PROMPT_TEMPLATE.format(
                question=question,
                context=context,
            )
            answer = self.invoke(user_input)
            mode = "rag"
        else:
            # 无检索结果 → 纯 LLM 模式
            logger.info("No docs found, falling back to pure LLM")
            answer = self.invoke(question)
            sources = []
            mode = "llm"

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "mode": mode,
        }
