"""治理模块：标准差计算、置信度区间判定、计数器生命周期。"""

import math
from enum import StrEnum


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def calculate_std(scores: list[int | float]) -> float:
    """计算分数列表的标准差（总体标准差）。"""
    if not scores:
        return 0.0
    n = len(scores)
    if n == 1:
        return 0.0
    mean = sum(scores) / n
    variance = sum((x - mean) ** 2 for x in scores) / n
    return math.sqrt(variance)


def evaluate_confidence(scores: list[int | float]) -> ConfidenceLevel:
    """根据分数列表计算置信度级别。"""
    sigma = calculate_std(scores)
    if sigma <= 5.0:
        return ConfidenceLevel.HIGH
    elif sigma <= 15.0:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


class GovernanceCounters:
    """治理计数器。"""

    def __init__(self):
        self.retry_counts: dict[str, int] = {}  # per-topic
        self.current_topic: str | None = None
        self.global_round_count: int = 0
        self.consecutive_medium: int = 0
        self.invalid_input_count: int = 0

    def get_retry_count(self, topic_id: str) -> int:
        return self.retry_counts.get(topic_id, 0)

    def increment_retry(self, topic_id: str) -> int:
        self.retry_counts[topic_id] = self.retry_counts.get(topic_id, 0) + 1
        return self.retry_counts[topic_id]

    def set_current_topic(self, topic_id: str) -> None:
        self.current_topic = topic_id
        # 新议题开始时重置该议题的 retry_count（不在这里 reset，只跟踪 current）

    def increment_global_round(self) -> None:
        self.global_round_count += 1

    def increment_consecutive_medium(self) -> None:
        self.consecutive_medium += 1

    def reset_consecutive_medium(self) -> None:
        self.consecutive_medium = 0

    def should_escalate(self) -> bool:
        """连续 3 次中置信度应触发熔断。"""
        return self.consecutive_medium >= 3

    def reset_for_new_topic(self, topic_id: str) -> None:
        self.retry_counts[topic_id] = 0
        self.current_topic = topic_id
