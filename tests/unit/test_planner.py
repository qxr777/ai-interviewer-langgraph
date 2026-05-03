"""T17: Planner 节点单元测试。

覆盖：mock LLM → 验证议题数 3-5、字段完整性、status=pending。
"""


def _get_planner():
    from src.agents.planner import NodePlanner

    return NodePlanner


class TestNodePlanner:
    """Planner 节点测试。"""

    def test_generates_topics(self, candidate_info_clean, job_description):
        """输入简历和 JD → 输出 3-5 个议题。"""
        planner_cls = _get_planner()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info=candidate_info_clean,
            routing_flag="CONTINUE",
        )

        planner = planner_cls(llm_model="mock", job_description=job_description)
        result = planner(state)

        assert "interview_plan" in result
        plan = result["interview_plan"]
        assert 3 <= len(plan) <= 5

    def test_topic_fields_complete(self, candidate_info_clean, job_description):
        """每个议题含 topic_id、topic_name、status=pending。"""
        planner_cls = _get_planner()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info=candidate_info_clean,
            routing_flag="CONTINUE",
        )

        planner = planner_cls(llm_model="mock", job_description=job_description)
        result = planner(state)

        for topic in result["interview_plan"]:
            assert "topic_id" in topic
            assert "topic_name" in topic
            assert topic["status"] == "pending"

    def test_planner_does_not_modify_candidate_info(self, candidate_info_clean, job_description):
        """Planner 不应修改候选人信息。"""
        planner_cls = _get_planner()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info=candidate_info_clean,
            routing_flag="CONTINUE",
        )

        planner = planner_cls(llm_model="mock", job_description=job_description)
        result = planner(state)

        assert "candidate_info" not in result
