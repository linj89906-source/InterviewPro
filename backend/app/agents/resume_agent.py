'''
简历分析 Agent

使用 LangChain with_structured_output 强制 LLM 返回结构化 JSON。
分析维度：基本信息提取、质量评分、优势/不足、修改建议、项目经历 STAR 改写。
'''

import json as _json
import re as _re
from typing import Optional
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent


# ---------- 结构化输出 Schema ----------

class BasicInfo(BaseModel):
    name: str = Field(default="", description="姓名")
    education: str = Field(default="", description="学历及学校")
    major: str = Field(default="", description="专业")
    years: str = Field(default="", description="工作年限/应届")
    target_role: str = Field(default="", description="求职意向岗位")
    skills: list[str] = Field(default_factory=list, description="技能列表")


class ProjectExperience(BaseModel):
    original: str = Field(default="", description="原始描述")
    optimized: str = Field(default="", description="STAR法则优化后描述")
    highlights: list[str] = Field(default_factory=list, description="亮点提炼")


class ResumeAnalysisResult(BaseModel):
    '''简历分析完整结果'''

    basic_info: BasicInfo = Field(default_factory=BasicInfo, description="基本信息")

    quality_score: float = Field(
        default=0.0,
        ge=0, le=100,
        description="简历综合质量评分 0-100"
    )

    score_breakdown: dict = Field(
        default_factory=lambda: {
            "内容完整性": 0,    # 是否包含必要模块
            "表达清晰度": 0,    # 语言是否精炼、逻辑清晰
            "技术匹配度": 0,    # 技能与目标岗位的匹配程度
            "成果量化度": 0,    # 是否有数据支撑的成果
            "排版专业性": 0,    # 结构、格式是否规范
        },
        description="各维度评分"
    )

    strengths: list[str] = Field(
        default_factory=list,
        description="简历优势，至少2条"
    )

    weaknesses: list[str] = Field(
        default_factory=list,
        description="简历不足，至少2条"
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="具体修改建议，至少3条"
    )

    optimized_projects: list[ProjectExperience] = Field(
        default_factory=list,
        description="优化后的项目经历（最多取前3个）"
    )

    hr_first_impression: str = Field(
        default="",
        description="模拟HR10秒浏览后的第一印象"
    )

    overall_assessment: str = Field(
        default="",
        description="综合评价（2-3句话）"
    )


# ---------- Agent ----------

RESUME_ANALYSIS_PROMPT = '''你是一位资深互联网 HR 和简历优化专家，拥有 10 年招聘经验。

## 你的任务
分析用户提供的简历文本，给出专业、具体的评估和优化建议。

## 分析要求

### 1. 基本信息提取
从简历中准确提取姓名、学历、学校、专业、工作年限、求职意向、技能列表。
如果简历中没有明确信息，字段留空。

### 2. 质量评分 (quality_score)
综合评分 0-100，需客观公正：
- 内容完整性 (25分)：是否包含教育、技能、项目/实习、个人亮点
- 表达清晰度 (25分)：语言精炼、逻辑清晰，无废话和空话
- 技术匹配度 (20分)：技能描述与目标岗位的匹配程度
- 成果量化度 (15分)：项目描述是否有具体数据支撑
- 排版专业性 (15分)：结构层次分明，格式规范

### 3. 优势分析 (strengths)
至少列出 2 条真实优势，不要虚假夸赞。
示例："项目经历中使用STAR法则描述，逻辑清晰"

### 4. 不足分析 (weaknesses)
至少列出 2 条真实不足，指出问题要具体。
示例："技能列表堆砌关键词，未体现掌握程度和实际应用场景"

### 5. 修改建议 (suggestions)
至少 3 条具体可操作的修改建议，每条建议说明"为什么"和"怎么做"。

### 6. 项目经历优化 (optimized_projects)
选取简历中的项目经历（最多3个），用STAR法则改写：
- Situation: 项目背景和目标
- Task: 你的职责
- Action: 具体行动和技术方案
- Result: 量化成果

### 7. HR第一印象 (hr_first_impression)
模拟HR快速浏览10秒后的真实感受，说明最吸引和最劝退的地方。

### 8. 综合评价 (overall_assessment)
2-3句话总结，说明这份简历的竞争力水平。

## 输出格式
必须严格按照 JSON Schema 输出，不要包含任何额外文本。
'''


class ResumeAgent(BaseAgent):
    '''简历分析 Agent'''

    SYSTEM_PROMPT = RESUME_ANALYSIS_PROMPT
    OUTPUT_SCHEMA = ResumeAnalysisResult
    temperature = 0.3
    max_tokens = 4096

    def analyze(self, resume_text: str) -> dict:
        '''分析简历文本，返回结构化结果。

        不用 invoke_with_json_fallback（其第一层 with_structured_output 与 DeepSeek 不兼容），
        直接 raw invoke + JSON 解析，与 ResumeMatchAgent 保持一致。
        '''
        import json as _json

        truncated = resume_text[:8000]

        # 把 JSON schema 嵌入 system prompt
        schema_hint = """
## 输出格式（严格按此 JSON，不要 markdown 代码块，只返回纯 JSON）
{
  "basic_info": {"name": "", "education": "", "major": "", "years": "", "target_role": "", "skills": []},
  "quality_score": 85,
  "score_breakdown": {"内容完整性": 20, "表达清晰度": 22, "技术匹配度": 18, "成果量化度": 13, "排版专业性": 12},
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["不足1", "不足2"],
  "suggestions": ["建议1", "建议2", "建议3"],
  "optimized_projects": [{"original": "", "optimized": "", "highlights": []}],
  "hr_first_impression": "HR 10秒浏览感受",
  "overall_assessment": "2-3句话综合评价"
}
只返回 JSON 对象，以 { 开头， } 结尾。"""
        self.SYSTEM_PROMPT = self.SYSTEM_PROMPT + schema_hint

        raw = self.invoke(truncated)
        json_str = ResumeMatchAgent._extract_json_text(raw)
        return _json.loads(json_str)


# ---------- JD Match Schema ----------

class JDMatchResult(BaseModel):
    """岗位匹配分析结果"""

    match_score: float = Field(
        default=0.0, ge=0, le=100,
        description="简历与目标岗位的综合匹配度 0-100"
    )

    score_breakdown: dict = Field(
        default_factory=lambda: {
            "技能匹配": 0,      # 技术栈是否对口
            "经验匹配": 0,      # 项目/实习经验的相关性
            "学历匹配": 0,      # 学历是否符合岗位要求
            "综合素质": 0,      # 沟通、团队协作等软实力体现
        },
        description="各维度匹配评分"
    )

    advantages: list[str] = Field(
        default_factory=list,
        description="针对该岗位的核心优势，至少2条"
    )

    risks: list[str] = Field(
        default_factory=list,
        description="简历中被刷掉的风险点，至少2条。如果简历优秀可以为空"
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="针对该岗位的改进建议。如果匹配度>=85且无明显风险，说明'无需大幅修改'并解释原因"
    )

    need_optimize: bool = Field(
        default=True,
        description="是否真的需要优化简历。匹配度>=85且无硬伤时为False"
    )

    optimize_reason: str = Field(
        default="",
        description="需要优化/不需要优化的具体原因"
    )

    interview_questions: list[str] = Field(
        default_factory=list,
        description="面试官针对这份简历可能追问的3-5个问题"
    )

    overall_verdict: str = Field(
        default="",
        description="综合评价，2-3句话"
    )


JD_MATCH_PROMPT = """你是一位资深互联网技术面试官和简历评估专家，拥有10年以上招聘经验。

## 你的任务
根据用户上传的简历内容，评估其与目标岗位的匹配度，给出客观、具体的反馈。

## 目标岗位要求
用户的目标岗位是：**{target_role}**

请你在脑海中构建该岗位的标准 JD（职责要求、必备技能、加分项），
然后逐项对比简历内容。

## 分析维度

### 1. 技能匹配
- 简历中的技术栈是否覆盖目标岗位的核心要求？
- 技能深度如何？（了解/熟悉/精通/源码级）
- 是否有该岗位特别看重的技术？

### 2. 经验匹配
- 项目/实习经历是否与岗位相关？
- 项目的技术难度和复杂度如何？
- 是否有该岗位期望的业务领域经验？

### 3. 学历匹配
- 学历层次是否达标？
- 专业是否对口？
- 学校背景是否有加分？

### 4. 综合素质
- 简历中是否体现了沟通、团队协作、学习能力等软实力？
- 是否有竞赛、开源贡献、技术博客等加分项？

## 关键原则：诚实判断

**如果简历确实优秀（匹配度 >= 85）：**
- 不要强行找缺点
- need_optimize 设为 false
- optimize_reason 说明"简历已能有效支撑该岗位的面试"
- suggestions 可以为空，或仅提出微调建议（如调整项目顺序）

**如果简历存在问题（匹配度 < 85）：**
- 明确指出被刷掉的风险点
- 给出具体可操作的修改方案
- need_optimize 设为 true

## 面试追问
针对简历中的项目经历和技术栈，预判面试官可能追问的3-5个问题。
例如：如果简历写了"使用Redis做缓存"，追问可能是"Redis缓存穿透怎么解决？"

## 输出格式
必须严格按照 JSON Schema 输出，不要包含任何额外文本。
"""


class ResumeMatchAgent(BaseAgent):
    """简历-岗位匹配分析 Agent。
    
    不使用 with_structured_output（DeepSeek 兼容性问题），
    而是在 system prompt 中嵌入 JSON schema 要求，通过 raw invoke + json parse。
    """

    temperature = 0.3
    max_tokens = 4096

    @staticmethod
    def _extract_json_text(text: str) -> str:
        """从文本中提取 JSON 部分"""
        text = text.strip()
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON found")
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        raise ValueError("Unmatched braces")

    def match(self, resume_text: str, target_role: str) -> dict:
        """分析简历与目标岗位的匹配度。

        Args:
            resume_text: 简历纯文本
            target_role: 目标岗位，如 "Java后端开发"

        Returns:
            匹配结果字典
        """
        # 动态构建 prompt（把 JSON schema 嵌入 system prompt）
        system_prompt = f"""你是一位资深互联网技术面试官和简历评估专家，拥有10年以上招聘经验。

## 你的任务
根据用户上传的简历内容，评估其与目标岗位「{target_role}」的匹配度。

## 分析要求
请你在脑海中构建该岗位的标准 JD，然后逐项对比简历：
1. 技能匹配：技术栈是否对口？深度如何？
2. 经验匹配：项目/实习是否相关？复杂度如何？
3. 学历匹配：学历层次、专业、学校背景
4. 综合素质：沟通、竞赛、开源、博客等加分项

## 核心原则：诚实判断
- 如果简历确实优秀（匹配度>=85），不要强行找缺点，need_optimize=false
- 如果简历有问题，明确指出风险点，need_optimize=true
- 如果简历技术栈完全不对口（如.NET简历投Java岗位），如实低分

## 面试追问
预判面试官针对这份简历可能追问的3-5个技术问题。

## 输出格式（严格按此 JSON，不要 markdown 代码块）
{{
  "match_score": 85,
  "advantages": ["优势1", "优势2"],
  "risks": ["风险点1", "风险点2"],
  "suggestions": ["建议1", "建议2"],
  "need_optimize": false,
  "optimize_reason": "需要优化/不需要优化的原因",
  "interview_questions": ["问题1", "问题2", "问题3"],
  "overall_verdict": "2-3句话综合评价"
}}

只返回 JSON 对象，以 {{ 开头， }} 结尾。"""

        self.SYSTEM_PROMPT = system_prompt
        truncated = resume_text[:8000]

        # Raw invoke + JSON extraction
        raw = self.invoke(truncated)
        json_str = self._extract_json_text(raw)
        return _json.loads(json_str)
