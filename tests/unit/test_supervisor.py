"""补充：Supervisor 节点测试。

覆盖：CONTINUE/SKIP/END 输入对应状态转换。
"""


def _get_supervisor():
    from src.agents.supervisor import NodeHumanSupervisor

    return NodeHumanSupervisor


class TestNodeHumanSupervisor:
    """Supervisor 节点 CLI 交互测试。"""

    def test_continue_input(self):
        """输入 CONTINUE → routing_flag 设为 CONTINUE。"""
        node_human_supervisor = _get_supervisor()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            routing_flag="ESCALATE",
            current_topic_id="topic_1",
        )

        supervisor = node_human_supervisor(mock_input="CONTINUE")
        result = supervisor(state)

        assert result.get("routing_flag") == "CONTINUE"

    def test_skip_input(self):
        """输入 SKIP → routing_flag 设为 CONTINUE，current_topic_index +1。"""
        node_human_supervisor = _get_supervisor()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            interview_plan=[
                {"topic_id": "topic_1", "topic_name": "A", "status": "in_progress"},
                {"topic_id": "topic_2", "topic_name": "B", "status": "pending"},
            ],
            current_topic_id="topic_1",
            current_topic_index=0,
            routing_flag="ESCALATE",
        )

        supervisor = node_human_supervisor(mock_input="SKIP")
        result = supervisor(state)

        assert result.get("current_topic_index") == 1
        assert result.get("current_topic_id") == "topic_2"

    def test_end_input(self):
        """输入 END → routing_flag 设为 END。"""
        node_human_supervisor = _get_supervisor()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            routing_flag="ESCALATE",
            current_topic_id="topic_1",
        )

        supervisor = node_human_supervisor(mock_input="END")
        result = supervisor(state)

        assert result.get("routing_flag") == "END"
