"""T12: 评估工具测试 — submit_evaluation 参数校验。

覆盖：score 越界、topic_id 不匹配、rationale 过短、合法提交。
"""

import pytest

# 足够长的理据（≥50 字符）
VALID_RATIONALE = "候选人在该议题上表现良好，回答准确且条理清晰，展示了扎实的专业基础知识和丰富的实践经验，对核心概念理解深刻。"


def _get_submit_evaluation():
    from src.tools.evaluation import submit_evaluation
    return submit_evaluation


class TestSubmitEvaluationValid:
    """合法提交评估。"""

    def test_valid_submission(self):
        submit_evaluation = _get_submit_evaluation()
        result = submit_evaluation(
            score=80,
            topic_id="topic_1",
            rationale=VALID_RATIONALE,
        )
        assert result["score"] == 80
        assert result["topic_id"] == "topic_1"

    def test_boundary_score_min(self):
        submit_evaluation = _get_submit_evaluation()
        result = submit_evaluation(
            score=1,
            topic_id="topic_1",
            rationale=VALID_RATIONALE,
        )
        assert result["score"] == 1

    def test_boundary_score_max(self):
        submit_evaluation = _get_submit_evaluation()
        result = submit_evaluation(
            score=100,
            topic_id="topic_1",
            rationale=VALID_RATIONALE,
        )
        assert result["score"] == 100


class TestSubmitEvaluationInvalid:
    """非法提交评估。"""

    def test_score_zero(self):
        submit_evaluation = _get_submit_evaluation()
        with pytest.raises(Exception):
            submit_evaluation(
                score=0,
                topic_id="topic_1",
                rationale=VALID_RATIONALE,
            )

    def test_score_101(self):
        submit_evaluation = _get_submit_evaluation()
        with pytest.raises(Exception):
            submit_evaluation(
                score=101,
                topic_id="topic_1",
                rationale=VALID_RATIONALE,
            )

    def test_score_negative(self):
        submit_evaluation = _get_submit_evaluation()
        with pytest.raises(Exception):
            submit_evaluation(
                score=-5,
                topic_id="topic_1",
                rationale=VALID_RATIONALE,
            )

    def test_rationale_too_short(self):
        """rationale 少于 50 字应抛异常。"""
        submit_evaluation = _get_submit_evaluation()
        with pytest.raises(Exception):
            submit_evaluation(
                score=80,
                topic_id="topic_1",
                rationale="太短了"
            )

    def test_rationale_empty(self):
        submit_evaluation = _get_submit_evaluation()
        with pytest.raises(Exception):
            submit_evaluation(
                score=80,
                topic_id="topic_1",
                rationale=""
            )

    def test_topic_id_empty(self):
        submit_evaluation = _get_submit_evaluation()
        with pytest.raises(Exception):
            submit_evaluation(
                score=80,
                topic_id="",
                rationale=VALID_RATIONALE,
            )
