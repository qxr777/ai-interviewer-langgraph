"""T25/T26: 图完整状态流转集成测试。

覆盖：正常路径（3 议题→报告）、重试路径（中置信度→CoT 重试）、熔断路径（σ>15→人工仲裁）。
"""


def _get_graph():
    from src.graph.builder import build_interview_graph

    return build_interview_graph


def _get_state_model():
    from src.state import InterviewState

    return InterviewState


def _run_graph(graph, initial_state, thread_id="test", max_cycles=20):
    """循环运行图直到报告生成或达到最大循环次数。

    每次 invoke 会跑一个议题周期然后停在 pause 节点。
    需要多次 invoke 直到所有议题完成。
    """
    config = {"configurable": {"thread_id": thread_id}}
    state = initial_state
    for _ in range(max_cycles):
        result = graph.invoke(state, config=config)
        # 如果已生成报告或所有议题已完成，返回
        if result.get("report") is not None:
            return result
        plan = result.get("interview_plan", [])
        all_done = all((t["status"] == "completed" if isinstance(t, dict) else t.status == "completed") for t in plan)
        if all_done:
            return result
        state = result
    return result


class TestGraphNormalFlow:
    """T25: 正常路径集成测试。"""

    def test_full_interview_flow(self, candidate_info_clean, job_description):
        """空状态启动 → 经历议题 → 输出面试报告 JSON。"""
        build_interview_graph = _get_graph()
        interview_state_model = _get_state_model()

        graph = build_interview_graph(llm_model="mock")
        initial_state = interview_state_model(
            candidate_info=candidate_info_clean,
            routing_flag="CONTINUE",
        )

        result = _run_graph(graph, initial_state, "normal-1")

        assert result.get("routing_flag") == "CONTINUE" or result.get("routing_flag") == "END"
        assert result.get("report") is not None
        assert result["report"]["status"] == "completed"

    def test_all_topics_completed(self, candidate_info_clean, job_description):
        """正常路径下所有议题应标记为 completed。"""
        build_interview_graph = _get_graph()
        interview_state_model = _get_state_model()

        graph = build_interview_graph(llm_model="mock")
        initial_state = interview_state_model(
            candidate_info=candidate_info_clean,
            routing_flag="CONTINUE",
        )

        result = _run_graph(graph, initial_state, "normal-2")

        plan = result.get("interview_plan", [])
        for topic in plan:
            status = topic["status"] if isinstance(topic, dict) else topic.status
            assert status == "completed"

    def test_report_has_scores(self, candidate_info_clean, job_description):
        """报告中应包含各议题的评分。"""
        build_interview_graph = _get_graph()
        interview_state_model = _get_state_model()

        graph = build_interview_graph(llm_model="mock")
        initial_state = interview_state_model(
            candidate_info=candidate_info_clean,
            routing_flag="CONTINUE",
        )

        result = _run_graph(graph, initial_state, "normal-3")
        report = result.get("report", {})
        topics = report.get("topics", [])

        assert len(topics) >= 3
        for topic in topics:
            assert topic["average_score"] is not None
            assert len(topic["scores"]) >= 3


class TestGraphRetryFlow:
    """T26: 重试路径集成测试。"""

    def test_medium_confidence_triggers_retry(self, candidate_info_clean, job_description):
        """模拟 σ 在中等区间 → 触发 CoT 重试 → 重试后应继续。"""
        build_interview_graph = _get_graph()
        interview_state_model = _get_state_model()

        graph = build_interview_graph(
            llm_model="mock",
            mock_sigma=10.0,  # 中置信度
        )
        initial_state = interview_state_model(
            candidate_info=candidate_info_clean,
            routing_flag="CONTINUE",
        )

        result = _run_graph(graph, initial_state, "retry-1")
        # 重试后最终应完成
        assert result.get("report") is not None


class TestGraphEscalationFlow:
    """T26: 熔断路径集成测试。"""

    def test_low_confidence_triggers_escalation(self, candidate_info_clean, job_description):
        """模拟 σ > 15 → 图挂起到 Human_Supervisor → 人工输入后恢复。"""
        build_interview_graph = _get_graph()
        interview_state_model = _get_state_model()

        graph = build_interview_graph(
            llm_model="mock",
            mock_sigma=20.0,  # 低置信度
            supervisor_mock_input="END",
        )
        initial_state = interview_state_model(
            candidate_info=candidate_info_clean,
            routing_flag="CONTINUE",
        )

        result = _run_graph(graph, initial_state, "escalate-1")
        # 人工输入 END 后应进入 REPORTING
        assert result.get("report") is not None
