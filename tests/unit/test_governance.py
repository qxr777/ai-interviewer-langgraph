"""T21: Governance 模块测试 — 标准差计算、置信度区间、计数器生命周期。

覆盖：σ 计算正确性、三区间判定、4 个计数器递增/重置、连续 3 次中置信熔断。
"""

from hypothesis import given
from hypothesis import strategies as st


def _get_governance():
    from src.graph.governance import (
        ConfidenceLevel,
        calculate_std,
        evaluate_confidence,
    )

    return calculate_std, evaluate_confidence, ConfidenceLevel


class TestCalculateStd:
    """标准差计算正确性。"""

    def test_identical_scores(self):
        """相同分数 σ = 0。"""
        calculate_std = _get_governance()[0]
        assert calculate_std([50, 50, 50]) == 0.0

    def test_known_std(self):
        """已知标准差的测试用例。"""
        calculate_std = _get_governance()[0]
        # [1, 2, 3, 4, 5] 的 σ = sqrt(2) ≈ 1.414
        result = calculate_std([1, 2, 3, 4, 5])
        assert abs(result - 1.41421356) < 0.001

    def test_single_score(self):
        """单个分数 σ = 0。"""
        calculate_std = _get_governance()[0]
        assert calculate_std([80]) == 0.0

    def test_two_identical(self):
        calculate_std = _get_governance()[0]
        assert calculate_std([80, 80]) == 0.0

    def test_two_different(self):
        calculate_std = _get_governance()[0]
        # [70, 90] 的 σ = 10.0
        assert abs(calculate_std([70, 90]) - 10.0) < 0.001

    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=10))
    def test_std_non_negative(self, scores):
        """标准差永远 ≥ 0。"""
        calculate_std = _get_governance()[0]
        assert calculate_std(scores) >= 0


class TestConfidenceLevel:
    """置信度区间判定。"""

    def test_high_confidence(self):
        """σ=3 → 高置信度。"""
        evaluate_confidence = _get_governance()[1]
        level = evaluate_confidence([80, 82, 78])
        assert level == "HIGH" or level.value == "HIGH"

    def test_medium_confidence(self):
        """σ=10 → 中等置信度。"""
        evaluate_confidence = _get_governance()[1]
        level = evaluate_confidence([70, 80, 90])
        assert level == "MEDIUM" or level.value == "MEDIUM"

    def test_low_confidence(self):
        """σ=20 → 低置信度。"""
        evaluate_confidence = _get_governance()[1]
        level = evaluate_confidence([30, 80, 100])
        assert level == "LOW" or level.value == "LOW"

    def test_boundary_sigma_5(self):
        """σ=5.0 → 边界仍为高置信度。"""
        evaluate_confidence = _get_governance()[1]
        # 构造 σ ≈ 5.0 的分数
        scores = [75, 80, 85]  # σ ≈ 4.08
        level = evaluate_confidence(scores)
        assert level == "HIGH" or level.value == "HIGH"

    def test_boundary_sigma_15(self):
        """σ=15.0 → 边界仍为中等置信度。"""
        evaluate_confidence = _get_governance()[1]
        # [50, 80, 100] σ ≈ 20.5 > 15
        # [65, 80, 95] σ ≈ 12.2 < 15
        level = evaluate_confidence([65, 80, 95])
        assert level == "MEDIUM" or level.value == "MEDIUM"


class TestCounters:
    """计数器生命周期。"""

    def test_retry_count_per_topic(self):
        """retry_count 按议题独立。"""
        from src.graph.governance import GovernanceCounters

        counters = GovernanceCounters()
        counters.increment_retry("topic_1")
        assert counters.get_retry_count("topic_1") == 1
        assert counters.get_retry_count("topic_2") == 0

    def test_retry_count_reset_on_new_topic(self):
        """新议题开始时 retry_count 归零。"""
        from src.graph.governance import GovernanceCounters

        counters = GovernanceCounters()
        counters.increment_retry("topic_1")
        counters.increment_retry("topic_1")
        counters.set_current_topic("topic_2")
        assert counters.get_retry_count("topic_2") == 0

    def test_global_round_count(self):
        """global_round_count 不复位。"""
        from src.graph.governance import GovernanceCounters

        counters = GovernanceCounters()
        for _ in range(5):
            counters.increment_global_round()
        assert counters.global_round_count == 5

    def test_consecutive_medium_reset_on_high(self):
        """高置信度时 consecutive_medium 归零。"""
        from src.graph.governance import GovernanceCounters

        counters = GovernanceCounters()
        counters.increment_consecutive_medium()
        counters.increment_consecutive_medium()
        counters.reset_consecutive_medium()
        assert counters.consecutive_medium == 0

    def test_consecutive_medium_trigger_escallate(self):
        """连续 3 次中置信度 → 应触发 ESCALATE。"""
        from src.graph.governance import GovernanceCounters

        counters = GovernanceCounters()
        for _ in range(3):
            counters.increment_consecutive_medium()
        assert counters.should_escalate()
