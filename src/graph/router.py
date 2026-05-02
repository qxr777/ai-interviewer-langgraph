"""路由模块：σ 分析 → CONTINUE/RETRY/ESCALATE/END 决策。"""

from enum import Enum

from src.graph.governance import GovernanceCounters


class RoutingDecision(str, Enum):
    QUESTIONER = "QUESTIONER"
    EVALUATOR = "EVALUATOR"
    SUPERVISOR = "ESCALATE"
    REPORTING = "REPORTING"


def route_next_node(
    sigma: float,
    counters: GovernanceCounters,
    interview_plan: list[dict],
    current_topic_id: str | None,
    current_topic_index: int,
) -> RoutingDecision:
    """基于 σ 和计数器决定下一步走向。

    状态转换表（覆盖 p2-plan-specs 第 4.1.2 节）:
    - σ ≤ 5.0 → 高置信度 → QUESTIONER（下一议题）
    - 5.0 < σ ≤ 15.0 → 中置信度 → QUESTIONER（重试/CoT）
    - σ > 15.0 → 低置信度 → ESCALATE
    - retry_count ≥ 3 → 跳过或 REPORTING
    - consecutive_medium ≥ 3 → ESCALATE
    - global_round_count ≥ 30 → REPORTING
    - 无更多议题 → REPORTING
    """
    # 全局限制检查
    if counters.global_round_count >= 30:
        return RoutingDecision.REPORTING

    # 连续中置信度熔断
    if counters.should_escalate():
        return RoutingDecision.SUPERVISOR

    # 检查是否有更多待完成议题
    has_more = any(t["status"] == "pending" for t in interview_plan)

    if sigma <= 5.0:
        # 高置信度
        counters.reset_consecutive_medium()
        if not has_more:
            return RoutingDecision.REPORTING
        return RoutingDecision.QUESTIONER

    elif sigma <= 15.0:
        # 中置信度
        counters.increment_consecutive_medium()

        # 检查是否连续 3 次中置信
        if counters.should_escalate():
            return RoutingDecision.SUPERVISOR

        # 检查当前议题重试次数
        retry = counters.get_retry_count(current_topic_id or "")
        if retry >= 3:
            # 跳过当前议题
            if not has_more:
                return RoutingDecision.REPORTING
            return RoutingDecision.QUESTIONER

        return RoutingDecision.QUESTIONER

    else:
        # 低置信度 → 熔断
        return RoutingDecision.SUPERVISOR
