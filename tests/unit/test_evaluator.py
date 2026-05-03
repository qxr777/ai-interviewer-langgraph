"""T17: Evaluator 节点单元测试。

覆盖：N=3 并行评分、score 范围、rationale 长度、topic_id 匹配。
"""


def _get_evaluator():
    from src.agents.evaluator import node_parallel_evaluator

    return node_parallel_evaluator


class TestNodeParallelEvaluator:
    """Evaluator 节点测试。"""

    def test_returns_n_scores(self, mock_interview_plan, mock_evaluation_scores):
        """N=3 并行调用 → 返回 3 个评分。"""
        node_parallel_evaluator = _get_evaluator()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            chat_history=[
                {"role": "ai", "content": "请解释装饰器", "topic_id": "topic_1"},
                {"role": "candidate", "content": "装饰器是 Python 的高阶函数...", "topic_id": "topic_1"},
            ],
            routing_flag="CONTINUE",
        )

        evaluator = node_parallel_evaluator(llm_model="mock", evaluator_count=3)
        result = evaluator(state)

        assert "evaluation_records" in result
        assert len(result["evaluation_records"]) == 3

    def test_score_in_range(self, mock_interview_plan, mock_evaluation_scores):
        """每个 score ∈ [1, 100]。"""
        node_parallel_evaluator = _get_evaluator()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            chat_history=[
                {"role": "ai", "content": "请解释装饰器", "topic_id": "topic_1"},
                {"role": "candidate", "content": "装饰器是 Python 的高阶函数...", "topic_id": "topic_1"},
            ],
            routing_flag="CONTINUE",
        )

        evaluator = node_parallel_evaluator(llm_model="mock", evaluator_count=3)
        result = evaluator(state)

        for record in result["evaluation_records"]:
            assert 1 <= record["score"] <= 100

    def test_rationale_min_length(self, mock_interview_plan, mock_evaluation_scores):
        """每个 rationale 长度 ≥ 50。"""
        node_parallel_evaluator = _get_evaluator()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            chat_history=[
                {"role": "ai", "content": "请解释装饰器", "topic_id": "topic_1"},
                {"role": "candidate", "content": "装饰器是 Python 的高阶函数...", "topic_id": "topic_1"},
            ],
            routing_flag="CONTINUE",
        )

        evaluator = node_parallel_evaluator(llm_model="mock", evaluator_count=3)
        result = evaluator(state)

        for record in result["evaluation_records"]:
            assert len(record["rationale"]) >= 50

    def test_topic_id_matches(self, mock_interview_plan, mock_evaluation_scores):
        """每个 topic_id 应匹配 current_topic_id。"""
        node_parallel_evaluator = _get_evaluator()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            chat_history=[
                {"role": "ai", "content": "请解释装饰器", "topic_id": "topic_1"},
                {"role": "candidate", "content": "装饰器是 Python 的高阶函数...", "topic_id": "topic_1"},
            ],
            routing_flag="CONTINUE",
        )

        evaluator = node_parallel_evaluator(llm_model="mock", evaluator_count=3)
        result = evaluator(state)

        for record in result["evaluation_records"]:
            assert record["topic_id"] == "topic_1"
