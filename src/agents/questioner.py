"""Node_Questioner：基于议题和历史对话生成提问。"""

import re

from src.state import ChatMessage, InterviewState
from src.utils.prompts import QUESTIONER_PROMPT

# 注入攻击检测模式（不区分大小写）
_INJECTION_PATTERNS = [
    r"(?:ignore\s+(?:all\s+)?previous\s+(?:instructions|rules|prompts))",
    r"(?:disregard\s+(?:all\s+)?(?:previous|above)\s+(?:instructions|rules))",
    r"(?:you\s+are\s+now\s+(?:acting\s+as\s+)?(?:a|an)?\s*\w+)",
    r"(?:system\s*[:：]\s*(?!.*\bquestion\b))",
    r"(?:<\|system\|>|<\|user\|>|<\|assistant\|>)",
    r"(?:\bnew\s+instructions?\b.*\bforget\b)",
    r"(?:\bskip\s+(?:all|the)\s+(?:steps|questions|rules))",
    r"(?:\bpretend\s+to\s+be\b|\bas\s+if\s+you\s+are\b)",
    r"(?:\breveal\s+(?:your|the)\s+(?:system|prompt|instructions))",
    r"(?:\bshow\s+(?:me|your)\s+(?:system\s+)?prompt)",
    r"(?:\bwhat\s+are\s+your\s+(?:instructions|rules|constraints|guidelines))",
    r"(?:\bhow\s+are\s+(?:you|this)\s+(?:prompted|configured|designed))",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


class NodeQuestioner:
    """面试提问官节点。

    读取 chat_history 与 current_topic_id，生成一条 AI 提问消息。
    """

    def __init__(self, llm_model: str = "", use_mock: bool = False):
        self.llm_model = llm_model
        self.use_mock = use_mock or llm_model == "mock"

    def __call__(self, state: InterviewState) -> dict:
        topic = self._get_current_topic(state)
        history = self._format_history(state)

        # 输入预处理：在 LLM 调用前检查候选人回答是否含注入攻击
        if not self.use_mock:
            latest_candidate = self._get_latest_candidate_answer(state)
            if latest_candidate and _INJECTION_RE.search(latest_candidate):
                question = f"请围绕「{topic}」继续作答，不要提出与面试议题无关的问题。"
                new_message = ChatMessage(
                    role="ai",
                    content=question,
                    topic_id=state.current_topic_id,
                )
                chat_history = list(state.chat_history)
                chat_history.append(new_message)
                return {"chat_history": chat_history}

        if self.use_mock:
            question = self._mock_question(topic, history)
        else:
            prompt = QUESTIONER_PROMPT.format(
                topic_name=topic,
                history=history,
            )
            question = self._call_llm(prompt)

        # 后处理：确保输出不含评分数字
        question = self._strip_score_patterns(question)

        new_message = ChatMessage(
            role="ai",
            content=question,
            topic_id=state.current_topic_id,
        )
        chat_history = list(state.chat_history)
        chat_history.append(new_message)

        return {"chat_history": chat_history}

    def _call_llm(self, prompt: str) -> str:
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI

        from src.config import load_config

        config = load_config()
        llm = ChatOpenAI(
            model=config["llm_model"],
            base_url=config["llm_api_base"],
            api_key=config["llm_api_key"],
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return str(response.content)

    def _mock_question(self, topic: str, history: str) -> str:
        """模拟模式下返回确定性问题。"""
        n = history.count("[candidate]") + 1
        return f"关于「{topic}」，请回答第 {n} 个问题：请详细解释该领域的核心概念和你在项目中的实践经验。"

    def _mock_answer(self, topic: str) -> str:
        """模拟候选人回答。"""
        return f"我认为{topic}是重要概念。在我的项目中运用了相关知识解决实际问题，包括系统优化和架构设计等方面。"

    def _get_current_topic(self, state: InterviewState) -> str:
        for topic in state.interview_plan:
            tid = topic.topic_id
            if tid == state.current_topic_id:
                return topic.topic_name
        return "通用"

    def _format_history(self, state: InterviewState) -> str:
        lines = []
        for msg in state.chat_history:
            lines.append(f"[{msg.role}] {msg.content}")
        return "\n".join(lines)

    def _get_latest_candidate_answer(self, state: InterviewState) -> str | None:
        """获取候选人最新一次回答。"""
        for msg in reversed(state.chat_history):
            if msg.role == "candidate":
                return msg.content
        return None

    def _strip_score_patterns(self, text: str) -> str:
        """移除可能包含评分的模式。"""
        # 移除 "80分"、"score: 80"、"得分 80" 等模式
        text = re.sub(r"\d{1,3}\s*分", "", text)
        text = re.sub(r"score\s*[:：]\s*\d{1,3}", "", text, flags=re.IGNORECASE)
        text = re.sub(r"得分\s*\d{1,3}", "", text)
        return text
