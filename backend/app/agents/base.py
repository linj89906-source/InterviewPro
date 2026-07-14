# -*- coding: utf-8 -*-
"""
Agent 基础模块 - 统一 LLM 调用封装

使用 LangChain ChatOpenAI 兼容 DeepSeek/OpenAI 接口。
每个子 Agent 继承 BaseAgent，只需定义 system_prompt 和输出 schema。

v2: invoke() 支持 history 参数，用 LangChain 原生消息格式传递对话历史。
"""

import json
import re
import logging
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> str:
    """从 LLM 返回的文本中提取纯 JSON 部分。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    depth = 0
    end = start
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if depth != 0:
        raise ValueError("Unmatched braces in JSON response")

    return text[start:end]


class BaseAgent:
    """
    Agent 基类。

    用法：
        class ResumeAgent(BaseAgent):
            SYSTEM_PROMPT = "你是简历分析专家..."
            OUTPUT_SCHEMA = ResumeAnalysisResult  # Pydantic model

        # 带对话历史的调用
        agent.invoke("当前问题", history=[
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ])
    """

    SYSTEM_PROMPT: str = ""
    OUTPUT_SCHEMA: Optional[Type[BaseModel]] = None
    temperature: float = 0.3
    max_tokens: int = 4096

    def __init__(self):
        self._llm: Optional[ChatOpenAI] = None

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = ChatOpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                model=OPENAI_MODEL,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        return self._llm

    def _build_messages(self, user_input: str, history: list[dict] | None = None) -> list:
        """构建发送给 LLM 的消息列表。

        格式：[SystemMessage, ...history_messages, HumanMessage]
        历史消息按 role 转为 AIMessage / HumanMessage。
        """
        messages = [SystemMessage(content=self.SYSTEM_PROMPT)]

        if history:
            for h in history:
                if h["role"] == "user":
                    messages.append(HumanMessage(content=h["content"]))
                elif h["role"] == "assistant":
                    messages.append(AIMessage(content=h["content"]))
                # 跳过 system 角色（不应出现在历史中）

        messages.append(HumanMessage(content=user_input))
        return messages

    def invoke(self, user_input: str, history: list[dict] | None = None) -> str:
        """调用 LLM，返回原始文本。支持传入对话历史。"""
        messages = self._build_messages(user_input, history)
        response = self.llm.invoke(messages)
        return response.content

    def invoke_structured(self, user_input: str) -> dict:
        """调用 LLM，强制返回结构化 JSON。"""
        if self.OUTPUT_SCHEMA is None:
            raise ValueError("OUTPUT_SCHEMA must be set to use invoke_structured")

        messages = self._build_messages(user_input)
        structured_llm = self.llm.with_structured_output(self.OUTPUT_SCHEMA)
        result = structured_llm.invoke(messages)
        if isinstance(result, BaseModel):
            return result.model_dump()
        return result

    def invoke_with_json_fallback(self, user_input: str) -> dict:
        """
        结构化调用 -> raw text -> JSON 提取，三层兜底。
        """
        last_raw = "(no response)"
        try:
            return self.invoke_structured(user_input)
        except Exception as e1:
            logger.info("Structured output failed (%s), trying raw parse", e1)

        try:
            last_raw = self.invoke(user_input)
            json_str = _extract_json(last_raw)
            return json.loads(json_str)
        except Exception as e2:
            logger.warning("Raw JSON parse failed (%s), retrying with hint", e2)

        try:
            user_input += (
                "\n\n【重要】请只返回 JSON 对象，不要附带任何解释、注释或后续文字。"
                "以 { 开头，以 } 结尾。"
            )
            last_raw = self.invoke(user_input)
            json_str = _extract_json(last_raw)
            return json.loads(json_str)
        except Exception as e3:
            raise ValueError(
                f"Failed to parse LLM response as JSON after 3 attempts. "
                f"Last raw response (first 500 chars): {last_raw[:500]}"
            ) from e3
