"""Node_Planner：简历解析 + 面试大纲生成。"""

import json
import re

from src.state import InterviewState
from src.utils.prompts import PLANNER_PROMPT


class NodePlanner:
    """面试统筹官节点。

    读取 candidate_info 和岗位 JD，生成 3-5 个议题大纲。
    """

    def __init__(self, llm_model: str = "", job_description: str = "", use_mock: bool = False):
        self.llm_model = llm_model
        self.job_description = job_description
        self.use_mock = use_mock or llm_model == "mock"

    def __call__(self, state: InterviewState) -> dict:
        candidate_info = state.candidate_info

        if self.use_mock:
            plan = self._mock_plan(candidate_info)
        else:
            prompt = PLANNER_PROMPT.format(
                candidate_info=json.dumps(candidate_info, ensure_ascii=False),
                job_description=self.job_description,
            )
            plan = self._call_llm(prompt)

        return {"interview_plan": plan}

    def _call_llm(self, prompt: str) -> list[dict]:
        """调用真实 LLM。"""
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
        return self._parse_plan_from_text(str(response.content))

    def _parse_plan_from_text(self, text: str) -> list[dict]:
        """从 LLM 响应中提取 JSON 议题列表。"""
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                items = json.loads(match.group())
                return [
                    {"topic_id": item.get("topic_id", f"topic_{i+1}"),
                     "topic_name": item.get("topic_name", ""),
                     "status": "pending"}
                    for i, item in enumerate(items)
                ]
            except json.JSONDecodeError:
                pass
        # 兜底
        return self._default_plan()

    def _mock_plan(self, candidate_info: dict) -> list[dict]:
        """模拟模式下返回确定性议题。"""
        skills = candidate_info.get("skills", [])
        first_skill = skills[0] if skills else "Python"
        return [
            {"topic_id": "topic_1", "topic_name": f"{first_skill} 基础与进阶", "status": "pending"},
            {"topic_id": "topic_2", "topic_name": "系统设计与架构", "status": "pending"},
            {"topic_id": "topic_3", "topic_name": "数据库与性能优化", "status": "pending"},
            {"topic_id": "topic_4", "topic_name": "工程实践与 DevOps", "status": "pending"},
        ]

    def _default_plan(self) -> list[dict]:
        return [
            {"topic_id": "topic_1", "topic_name": "专业技能基础", "status": "pending"},
            {"topic_id": "topic_2", "topic_name": "项目经验", "status": "pending"},
            {"topic_id": "topic_3", "topic_name": "系统设计", "status": "pending"},
        ]
