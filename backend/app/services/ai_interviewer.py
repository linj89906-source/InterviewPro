import json
import httpx
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

SYSTEM_PROMPT = """你是专业的计算机面试官。你的职责：
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
"""

async def get_interview_response(
    user_message: str,
    conversation_history: list[dict],
    interview_config: dict
) -> dict:
    """调用LLM进行面试对话"""
    role = interview_config.get("role", "后端开发")
    company = interview_config.get("company", "")
    mode = interview_config.get("mode", "practice")

    mode_instructions = {
        "practice": "练习模式：温和引导，答错时给予提示后再追问",
        "mock": "模拟面试模式：严格计时，像真实面试一样施加适当压力",
        "quick": "快速模式：每题一问一答，给简短评分即进入下一题"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\n\n当前配置：目标岗位={role}，目标公司={company}，模式={mode_instructions.get(mode, mode_instructions['practice'])}。请用JSON格式回复。"}
    ] + conversation_history + [
        {"role": "user", "content": user_message}
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENAI_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
            }
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # Try to parse JSON from response (strip markdown code fences if present)
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(content)

async def evaluate_answer(
    question: str,
    user_answer: str,
    reference_answer: str = ""
) -> dict:
    """单独评估一道面试题的答案"""
    prompt = f"""面试题：{question}
考生答案：{user_answer}
参考答案：{reference_answer if reference_answer else "无"}

请以JSON格式评估并返回：{{"score": 整数0-100, "feedback": "详细反馈", "strengths": ["优点"], "weaknesses": ["不足"], "correct_points": ["正确点"], "missing_points": ["遗漏点"]}}"""

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": "你是计算机面试评估专家。严格但公正地评估答案。请始终以JSON格式回复。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 1500,
            }
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(content)