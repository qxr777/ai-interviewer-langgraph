"""T05: InterviewState 数据契约测试。

覆盖：合法实例化、字段类型校验、Enum 受限、嵌套校验、缺省值。
"""

import pytest
from pydantic import ValidationError


def _get_state():
    from src.state import InterviewState, RoutingFlag

    return InterviewState, RoutingFlag


class TestRoutingFlagEnum:
    """测试 RoutingFlag Enum 取值受限。"""

    def test_valid_values(self):
        routing_flag = _get_state()[1]
        for val in ["CONTINUE", "RETRY", "ESCALATE", "END"]:
            assert routing_flag(val) is not None

    def test_invalid_value(self):
        routing_flag = _get_state()[1]
        with pytest.raises(ValueError):
            routing_flag("INVALID")


class TestInterviewStateCreation:
    """合法实例化测试。"""

    def test_minimal_state(self):
        """最小字段可以创建状态。"""
        interview_state_model = _get_state()[0]
        state = interview_state_model(
            candidate_info={"name": "Test", "skills": []},
            routing_flag="CONTINUE",
        )
        assert state.candidate_info == {"name": "Test", "skills": []}
        assert state.routing_flag == "CONTINUE"

    def test_full_state(self, sample_state_data):
        """完整字段可以正常加载。"""
        interview_state_model = _get_state()[0]
        state = interview_state_model(**sample_state_data)
        assert state.current_topic_id == "topic_1"
        assert len(state.interview_plan) == 3
        assert state.routing_flag == "CONTINUE"

    def test_chat_history_with_messages(self):
        """chat_history 接受消息列表。"""
        interview_state_model = _get_state()[0]
        state = interview_state_model(
            candidate_info={"name": "Test", "skills": []},
            chat_history=[
                {"role": "system", "content": "hello"},
                {"role": "ai", "content": "请介绍一下自己", "topic_id": "t1"},
                {"role": "candidate", "content": "我是一名开发者", "topic_id": "t1"},
            ],
            routing_flag="CONTINUE",
        )
        assert len(state.chat_history) == 3


class TestInterviewStateValidation:
    """非法字段拒绝测试。"""

    def test_missing_required_fields(self):
        """缺少必填字段抛 ValidationError。"""
        interview_state_model = _get_state()[0]
        with pytest.raises(ValidationError):
            interview_state_model()

    def test_missing_candidate_info(self):
        interview_state_model = _get_state()[0]
        with pytest.raises(ValidationError):
            interview_state_model(routing_flag="CONTINUE")

    def test_missing_routing_flag(self):
        interview_state_model = _get_state()[0]
        with pytest.raises(ValidationError):
            interview_state_model(candidate_info={"name": "Test", "skills": []})

    def test_invalid_routing_flag_string(self):
        """非法的 routing_flag 字符串抛 ValidationError。"""
        interview_state_model = _get_state()[0]
        with pytest.raises(ValidationError):
            interview_state_model(
                candidate_info={"name": "Test", "skills": []},
                routing_flag="BOGUS",
            )

    def test_interview_plan_invalid_item(self):
        """interview_plan 中缺少必填字段抛 ValidationError。"""
        interview_state_model = _get_state()[0]
        with pytest.raises(ValidationError):
            interview_state_model(
                candidate_info={"name": "Test", "skills": []},
                interview_plan=[{"topic_name": "no_id"}],
                routing_flag="CONTINUE",
            )

    def test_evaluation_record_score_out_of_range(self):
        """evaluation_records 中 score 越界抛 ValidationError。"""
        interview_state_model = _get_state()[0]
        with pytest.raises(ValidationError):
            interview_state_model(
                candidate_info={"name": "Test", "skills": []},
                evaluation_records=[{"score": 101, "topic_id": "t1", "rationale": "x" * 50}],
                routing_flag="CONTINUE",
            )

    def test_evaluation_record_score_negative(self):
        interview_state_model = _get_state()[0]
        with pytest.raises(ValidationError):
            interview_state_model(
                candidate_info={"name": "Test", "skills": []},
                evaluation_records=[{"score": -1, "topic_id": "t1", "rationale": "x" * 50}],
                routing_flag="CONTINUE",
            )

    def test_evaluation_record_rationale_short_allowed(self):
        """rationale 长度不足 state 层允许（由工具层校验）。"""
        interview_state_model = _get_state()[0]
        state = interview_state_model(
            candidate_info={"name": "Test", "skills": []},
            evaluation_records=[{"score": 80, "topic_id": "t1", "rationale": "short"}],
            routing_flag="CONTINUE",
        )
        # Pydantic model, not dict
        assert state.evaluation_records[0].rationale == "short"


class TestInterviewStateDefaults:
    """缺省值测试。"""

    def test_default_empty_lists(self):
        """chat_history, interview_plan, evaluation_records 默认为空列表。"""
        interview_state_model = _get_state()[0]
        state = interview_state_model(
            candidate_info={"name": "Test", "skills": []},
            routing_flag="CONTINUE",
        )
        assert state.chat_history == []
        assert state.interview_plan == []
        assert state.evaluation_records == []

    def test_default_current_topic(self):
        """current_topic_id 和 current_topic_index 默认为 None/0。"""
        interview_state_model = _get_state()[0]
        state = interview_state_model(
            candidate_info={"name": "Test", "skills": []},
            routing_flag="CONTINUE",
        )
        assert state.current_topic_id is None
        assert state.current_topic_index == 0
