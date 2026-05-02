"""Node_Parallel_Evaluator：多路独立评分。"""

import json
import re

from src.state import InterviewState
from src.tools.evaluation import submit_evaluation
from src.utils.prompts import EVALUATOR_PROMPT


class NodeParallelEvaluator:
    """并行评估官节点。

    启动 N 个独立的评估进程对最后一次回答进行打分。
    """

    def __init__(self, llm_model: str = "", evaluator_count: int = 3, use_mock: bool = False):
        self.llm_model = llm_model
        self.evaluator_count = evaluator_count
        self.use_mock = use_mock or llm_model == "mock"

    def __call__(self, state: InterviewState) -> dict:
        answer = self._get_last_candidate_answer(state)
        topic = self._get_current_topic_name(state)

        records = []
        for i in range(self.evaluator_count):
            if self.use_mock:
                score, rationale = self._mock_score(i, answer)
            else:
                prompt = EVALUATOR_PROMPT.format(
                    topic_name=topic,
                    answer=answer,
                )
                score, rationale = self._call_llm(prompt)

            try:
                record = submit_evaluation(
                    score=score,
                    topic_id=state.current_topic_id or "unknown",
                    rationale=rationale,
                )
                records.append(record)
            except ValueError:
                # 校验失败，跳过该评估器
                continue

        return {"evaluation_records": records}

    def _call_llm(self, prompt: str) -> tuple[int, str]:
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
        return self._parse_evaluation_result(str(response.content))

    def _parse_evaluation_result(self, text: str) -> tuple[int, str]:
        """从 LLM 响应中提取 score 和 rationale。"""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                score = int(data.get("score", 75))
                rationale = data.get("rationale", "")
                if len(rationale) < 50:
                    rationale = rationale + "。" * max(0, 50 - len(rationale))
                return score, rationale
            except (json.JSONDecodeError, ValueError):
                pass
        return 75, "候选人回答基本符合要求，展示了相关知识和实践经验，整体表现良好。"

    def _mock_score(self, evaluator_index: int, answer: str) -> tuple[int, str]:
        """模拟模式下返回确定性评分。"""
        scores = [82, 78, 85]
        rationales = [
            "候选人展示了扎实的专业基础，能够清晰解释核心概念，并在回答中提到了实际项目中的应用场景。整体表现良好，对关键知识点掌握到位。",
            "回答内容基本正确，对核心概念的理解较为到位，但在某些高级特性方面略有欠缺。总体表现合格，建议进一步加强深度学习。",
            "候选人对相关技术有深入理解，不仅回答了基础概念，还主动提到了实践中遇到的问题和解决方案，表现出很强的综合能力。",
        ]
        idx = evaluator_index % len(scores)
        return scores[idx], rationales[idx]

    def _get_last_candidate_answer(self, state: InterviewState) -> str:
        for msg in reversed(state.chat_history):
            if msg.role == "candidate":
                return msg.content
        return ""

    def _get_current_topic_name(self, state: InterviewState) -> str:
        for topic in state.interview_plan:
            tid = topic.topic_id
            if tid == state.current_topic_id:
                return topic.topic_name
        return "通用"
