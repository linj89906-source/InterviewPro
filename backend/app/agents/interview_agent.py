'''
面试 Agent

负责面试对话和会话总结报告生成。
使用 BaseAgent + LangChain 统一 LLM 调用。
'''

from app.agents.base import BaseAgent


# ---------- 对话 Prompt ----------

INTERVIEW_SYSTEM_PROMPT = '''你是专业的计算机面试官。你的职责：
1. 根据用户的目标岗位和方向提出面试问题
2. 对用户的回答进行评分（0-100）和详细反馈
3. 根据回答质量决定是否深入追问或换新题
4. 模拟真实面试的压力和节奏

评分维度：正确性(40%)、深度(25%)、表达清晰度(20%)、实战经验(15%)
反馈需包含：优点、不足、标准答案要点、追问方向

你必须始终以JSON格式回复，不要输出任何其他内容。格式如下：
{"type": "question", "content": "面试官说的话", "score": 0, "feedback_detail": {"strengths": [], "weaknesses": [], "reference_answer": "", "next_direction": ""}, "topic": "", "difficulty": "medium"}
或 {"type": "feedback", "content": "...", "score": 85, "feedback_detail": {...}}
或 {"type": "follow_up", "content": "...", "score": 0, "feedback_detail": {...}}
或 {"type": "summary", "content": "...", "score": 80, "feedback_detail": {...}}
'''

# ---------- 报告生成 Prompt ----------

REPORT_SYSTEM_PROMPT = '''你是一位资深面试评估专家。根据面试对话记录，生成一份全面的面试评估报告。

## 报告结构

### 1. 总体评分 (overall_score)
综合所有问答，给出 0-100 的总分。

### 2. 各题评分 (question_scores)
对每道题单独评分并说明理由。

### 3. 优势总结 (strengths_summary)
候选人在面试中表现出的 3-5 个突出优势。

### 4. 待改进领域 (improvement_areas)
3-5 个需要重点提升的方向，每个说明原因和具体建议。

### 5. 知识领域评估 (domain_assessment)
按技术领域拆分评估（如 Java基础、数据库、系统设计等），
标注掌握程度：精通/熟练/了解/薄弱。

### 6. 学习建议 (learning_plan)
具体的下一步学习建议，按优先级排序。

### 7. 面试建议 (interview_tips)
针对该候选人的面试技巧建议。

### 8. 综合评价 (overall_comment)
一段话总结。

## 输出格式
必须返回严格的 JSON，格式如下：
{
  "overall_score": 75,
  "question_scores": [{"question": "问题内容", "answer": "用户回答", "score": 80, "comment": "评分理由"}],
  "strengths_summary": ["优势1", "优势2"],
  "improvement_areas": [{"area": "领域", "reason": "原因", "suggestion": "建议"}],
  "domain_assessment": [{"domain": "Java基础", "level": "熟练", "detail": "说明"}],
  "learning_plan": ["建议1", "建议2"],
  "interview_tips": ["技巧1", "技巧2"],
  "overall_comment": "综合评价"
}
'''


class InterviewAgent(BaseAgent):
    '''面试 Agent — 报告生成'''

    SYSTEM_PROMPT = REPORT_SYSTEM_PROMPT
    temperature = 0.3
    max_tokens = 4096

    def generate_report(self, records: list[dict], role: str = "") -> dict:
        '''
        根据面试记录生成评估报告。

        Args:
            records: 面试记录列表，每条包含 question/user_answer/score 等
            role: 目标岗位
        '''
        if not records:
            return {"error": "没有面试记录"}

        # 构建上下文
        context_parts = [f"目标岗位：{role}" if role else "目标岗位：未指定"]
        context_parts.append("\n面试问答记录：\n")

        for i, rec in enumerate(records, 1):
            q = rec.get("question_text", "")
            a = rec.get("user_answer", "")
            s = rec.get("score", 0)
            fb = rec.get("ai_feedback", "")
            context_parts.append(
                f"--- 第{i}题 ---\n"
                f"问题：{q}\n"
                f"回答：{a}\n"
                f"评分：{s}\n"
                f"AI反馈：{fb}\n"
            )

        user_input = "\n".join(context_parts)
        return self.invoke_with_json_fallback(user_input)
