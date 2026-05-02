"""T21: Router 模块测试 — 路由决策分支覆盖。

覆盖：σ ≤ 5 → CONTINUE、σ = 10 → RETRY、σ = 20 → ESCALATE、无更多议题 → END。
"""

import pytest


def _get_router():
    from src.graph.router import route_next_node, RoutingDecision
    return route_next_node, RoutingDecision


class TestRouterBasic:
    """基本路由决策。"""

    def test_sigma_3_continue(self, mock_interview_plan):
        """σ=3（高置信度）→ 流转至 Questioner。"""
        route_next_node = _get_router()[0]
        from src.graph.governance import GovernanceCounters
        counters = GovernanceCounters()

        decision = route_next_node(
            sigma=3.0,
            counters=counters,
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            current_topic_index=0,
        )
        assert decision == "QUESTIONER" or decision.value == "QUESTIONER"

    def test_sigma_10_retry_first_attempt(self, mock_interview_plan):
        """σ=10（中置信度），retry_count=0 → RETRY（CoT 重试）。"""
        route_next_node = _get_router()[0]
        from src.graph.governance import GovernanceCounters
        counters = GovernanceCounters()

        decision = route_next_node(
            sigma=10.0,
            counters=counters,
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            current_topic_index=0,
        )
        assert decision == "QUESTIONER" or decision.value == "QUESTIONER"

    def test_sigma_20_escalate(self, mock_interview_plan):
        """σ=20（低置信度）→ ESCALATE。"""
        route_next_node = _get_router()[0]
        from src.graph.governance import GovernanceCounters
        counters = GovernanceCounters()

        decision = route_next_node(
            sigma=20.0,
            counters=counters,
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            current_topic_index=0,
        )
        assert decision == "ESCALATE" or decision.value == "ESCALATE"

    def test_no_more_topics_end(self):
        """无更多待完成议题 → REPORTING。"""
        route_next_node = _get_router()[0]
        from src.graph.governance import GovernanceCounters
        counters = GovernanceCounters()

        completed_plan = [
            {"topic_id": "topic_1", "topic_name": "A", "status": "completed"},
            {"topic_id": "topic_2", "topic_name": "B", "status": "completed"},
        ]

        decision = route_next_node(
            sigma=3.0,
            counters=counters,
            interview_plan=completed_plan,
            current_topic_id="topic_2",
            current_topic_index=1,
        )
        assert decision == "REPORTING" or decision.value == "REPORTING"


class TestRouterRetry:
    """重试路径。"""

    def test_retry_count_exceeds_max_skip(self, mock_interview_plan):
        """retry_count ≥ 3 → 跳过当前议题。"""
        route_next_node = _get_router()[0]
        from src.graph.governance import GovernanceCounters
        counters = GovernanceCounters()
        counters.retry_counts["topic_1"] = 3

        decision = route_next_node(
            sigma=10.0,
            counters=counters,
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            current_topic_index=0,
        )
        # 跳过当前议题，前往下一议题或 REPORTING
        assert decision in ("QUESTIONER", "REPORTING") or decision.value in ("QUESTIONER", "REPORTING")


class TestRouterGlobalLimits:
    """全局限制。"""

    def test_max_rounds_exceeded(self, mock_interview_plan):
        """global_round_count ≥ 30 → REPORTING。"""
        route_next_node = _get_router()[0]
        from src.graph.governance import GovernanceCounters
        counters = GovernanceCounters()
        counters.global_round_count = 30

        decision = route_next_node(
            sigma=3.0,
            counters=counters,
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            current_topic_index=0,
        )
        assert decision == "REPORTING" or decision.value == "REPORTING"

    def test_consecutive_medium_escalate(self, mock_interview_plan):
        """连续 3 次中置信度 → ESCALATE。"""
        route_next_node = _get_router()[0]
        from src.graph.governance import GovernanceCounters
        counters = GovernanceCounters()
        counters.consecutive_medium = 3

        decision = route_next_node(
            sigma=10.0,
            counters=counters,
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            current_topic_index=0,
        )
        assert decision == "ESCALATE" or decision.value == "ESCALATE"
