"""T27: 工具链端到端测试。

覆盖：简历解析 → 大纲生成 → 提问 → 评分全链路。
"""

import pytest


def _get_full_pipeline():
    from src.tools.resume_parser import parse_resume_document
    from src.agents.planner import NodePlanner
    from src.agents.questioner import NodeQuestioner
    from src.agents.evaluator import NodeParallelEvaluator
    from src.tools.evaluation import submit_evaluation
    return parse_resume_document, NodePlanner, NodeQuestioner, NodeParallelEvaluator, submit_evaluation


class TestToolchainEndToEnd:
    """完整工具链：mock_resume.pdf → 解析 → 大纲 → 提问 → 评分。"""

    def test_parse_to_plan(self, mock_resume_path, job_description):
        """简历解析 → 生成大纲。"""
        parse_resume_document, NodePlanner, _, _, _ = _get_full_pipeline()
        from src.state import InterviewState

        parsed = parse_resume_document(mock_resume_path)
        assert "name" in parsed or "skills" in parsed

        # 确保有 skills 字段且非空
        if not parsed.get("skills"):
            parsed["skills"] = ["Python"]

        state = InterviewState(
            candidate_info=parsed,
            routing_flag="CONTINUE",
        )
        planner = NodePlanner(llm_model="mock", job_description=job_description)
        result = planner(state)

        assert "interview_plan" in result
        assert 3 <= len(result["interview_plan"]) <= 5

    def test_question_to_evaluation(self, job_description):
        """提问 → 候选人回答 → 评估打分。"""
        _, NodePlanner, NodeQuestioner, NodeParallelEvaluator, submit_evaluation = _get_full_pipeline()
        from src.state import InterviewState

        candidate_info = {
            "name": "Test",
            "skills": ["Python", "FastAPI"],
            "experience_years": 3,
        }

        state = InterviewState(
            candidate_info=candidate_info,
            routing_flag="CONTINUE",
        )
        planner = NodePlanner(llm_model="mock", job_description=job_description)
        plan_result = planner(state)

        first_topic = plan_result["interview_plan"][0]
        tid = first_topic["topic_id"] if isinstance(first_topic, dict) else first_topic.topic_id

        state_dict = {
            "candidate_info": candidate_info,
            "interview_plan": plan_result["interview_plan"],
            "current_topic_id": tid,
            "current_topic_index": 0,
            "chat_history": [],
            "evaluation_records": [],
            "routing_flag": "CONTINUE",
        }
        state = InterviewState(**state_dict)

        # Questioner 提问 + mock 候选人回答
        questioner = NodeQuestioner(llm_model="mock")
        q_result = questioner(state)
        state = InterviewState(
            candidate_info=state.candidate_info,
            interview_plan=state.interview_plan,
            current_topic_id=state.current_topic_id,
            current_topic_index=state.current_topic_index,
            chat_history=q_result["chat_history"],
            evaluation_records=[],
            routing_flag="CONTINUE",
        )

        # Evaluator 评分
        evaluator = NodeParallelEvaluator(llm_model="mock", evaluator_count=3)
        e_result = evaluator(state)

        assert len(e_result["evaluation_records"]) == 3
        for record in e_result["evaluation_records"]:
            score = record["score"] if isinstance(record, dict) else record.score
            assert 1 <= score <= 100

    def test_submit_evaluation_validation(self):
        """submit_evaluation 的校验逻辑在 E2E 中也能覆盖。"""
        _, _, _, _, submit_eval = _get_full_pipeline()

        result = submit_eval(
            score=85,
            topic_id="topic_1",
            rationale="候选人在该议题上展示了扎实的基础知识和丰富的实践经验，回答准确且条理清晰，体现了较强的专业能力和深入的技术理解。"
        )
        assert result["score"] == 85
