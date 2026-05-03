"""LangGraph 图构建：节点注册 + 条件边 + 状态持久化。"""

import json
import signal
from datetime import datetime
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.graph.governance import GovernanceCounters, calculate_std
from src.graph.router import RoutingDecision, route_next_node
from src.state import InterviewState, RoutingFlag, TopicItem

_counters = GovernanceCounters()


def _to_state(x):
    if isinstance(x, InterviewState):
        return x
    if isinstance(x, dict):
        return InterviewState(**x)
    return InterviewState.model_validate(x)


def _to_dict(obj):
    if isinstance(obj, dict):
        return obj
    return obj.model_dump()


def generate_report(evaluation_records: list[dict], interview_plan: list[dict]) -> dict:
    """汇总 evaluation_records 为结构化 JSON 面试报告。"""
    if not evaluation_records:
        return {
            "status": "no_valid_evaluations",
            "topics": [],
            "generated_at": datetime.now().isoformat(),
        }

    topic_scores: dict[str, list] = {}
    topic_rationales: dict[str, list] = {}
    for rec in evaluation_records:
        tid = rec["topic_id"]
        topic_scores.setdefault(tid, []).append(rec["score"])
        topic_rationales.setdefault(tid, []).append(rec["rationale"])

    topics = []
    for topic in interview_plan:
        tid = topic["topic_id"]
        if tid in topic_scores:
            scores = topic_scores[tid]
            avg = sum(scores) / len(scores)
            topics.append(
                {
                    "topic_id": tid,
                    "topic_name": topic["topic_name"],
                    "status": topic.get("status", "completed"),
                    "average_score": round(avg, 2),
                    "scores": scores,
                    "rationales": topic_rationales.get(tid, []),
                }
            )
        else:
            topics.append(
                {
                    "topic_id": tid,
                    "topic_name": topic["topic_name"],
                    "status": topic.get("status", "pending"),
                    "average_score": None,
                    "scores": [],
                    "rationales": [],
                }
            )

    overall_scores = [t["average_score"] for t in topics if t["average_score"] is not None]
    overall_avg = sum(overall_scores) / len(overall_scores) if overall_scores else None

    return {
        "status": "completed",
        "overall_average_score": round(overall_avg, 2) if overall_avg else None,
        "topics": topics,
        "total_evaluations": len(evaluation_records),
        "generated_at": datetime.now().isoformat(),
    }


def _advance_topic(state: InterviewState) -> tuple[dict, str]:
    """标记当前议题完成，选择下一议题。返回状态更新字典。"""
    new_plan = []
    next_topic_id = None
    next_idx = None
    found_current = False

    for i, topic in enumerate(state.interview_plan):
        t = _to_dict(topic)
        if t["topic_id"] == state.current_topic_id:
            t["status"] = "completed"
            found_current = True
        elif found_current and t["status"] == "pending" and next_topic_id is None:
            next_topic_id = t["topic_id"]
            next_idx = i
        new_plan.append(t)

    plan_typed = [TopicItem(**t) if isinstance(t, dict) else t for t in new_plan]

    if next_topic_id:
        _counters.set_current_topic(next_topic_id)
        _counters.reset_consecutive_medium()
        return {
            "interview_plan": plan_typed,
            "current_topic_id": next_topic_id,
            "current_topic_index": next_idx,
        }, "questioner"
    else:
        return {
            "interview_plan": plan_typed,
        }, "reporting"


def _make_pause_node():
    """Pause 节点：无出边，图在此停止，等待用户回答后再次 invoke。"""

    def node(state):
        return {}

    return node


def build_interview_graph(
    llm_model: str = "",
    job_description: str = "",
    evaluator_count: int = 3,
    mock_sigma: float | None = None,
    force_consecutive_medium: int = 0,
    use_mock: bool = False,
    supervisor_mock_input: str | None = None,
):
    """构建 LangGraph 面试图。"""
    use_mock = use_mock or llm_model == "mock"

    from src.agents.evaluator import NodeParallelEvaluator
    from src.agents.planner import NodePlanner
    from src.agents.questioner import NodeQuestioner
    from src.agents.supervisor import NodeHumanSupervisor

    planner = NodePlanner(llm_model=llm_model, job_description=job_description, use_mock=use_mock)
    questioner = NodeQuestioner(llm_model=llm_model, use_mock=use_mock)
    evaluator = NodeParallelEvaluator(llm_model=llm_model, evaluator_count=evaluator_count, use_mock=use_mock)
    supervisor = NodeHumanSupervisor(llm_model=llm_model, mock_input=supervisor_mock_input)

    builder = StateGraph(InterviewState)

    # 节点
    builder.add_node("planner", _make_planner_node(planner))
    builder.add_node("questioner", _make_questioner_node(questioner))
    builder.add_node("evaluator", _make_evaluator_node(evaluator))
    builder.add_node("supervisor", _make_supervisor_node(supervisor))
    builder.add_node("reporting", _make_reporting_node())
    builder.add_node("router", _make_router_node(mock_sigma, force_consecutive_medium))
    builder.add_node("pause", _make_pause_node())

    # 边
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "questioner")
    builder.add_edge("questioner", "evaluator")
    builder.add_edge("evaluator", "router")
    builder.add_edge("supervisor", "router")
    builder.add_edge("reporting", END)
    # pause 节点无出边 — 图在此自然停止，等待用户回答

    # 路由条件边
    def route_edge(state: InterviewState) -> Literal["questioner", "supervisor", "reporting", "pause"]:
        s = _to_state(state)
        if s.next_node == "questioner":
            return "pause"
        result: Literal["questioner", "supervisor", "reporting", "pause"] = s.next_node  # type: ignore[assignment]
        return result

    builder.add_conditional_edges(
        "router",
        route_edge,
        {
            "questioner": "pause",
            "supervisor": "supervisor",
            "reporting": "reporting",
            "pause": "pause",
        },
    )

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    _setup_signal_handler(graph)

    return graph


def _make_planner_node(planner):
    def node(state):
        s = _to_state(state)
        # 如果已有议题列表，跳过 planner（避免重置已完成状态）
        if s.interview_plan:
            return {}
        result = planner(s)
        if "interview_plan" in result and not s.current_topic_id:
            first_topic = result["interview_plan"][0]
            tid = first_topic["topic_id"] if isinstance(first_topic, dict) else first_topic.topic_id
            result["current_topic_id"] = tid
            result["current_topic_index"] = 0
            _counters.set_current_topic(tid)
        return result

    return node


def _make_questioner_node(questioner):
    def node(state):
        s = _to_state(state)
        _counters.increment_global_round()
        return questioner(s)

    return node


def _make_evaluator_node(evaluator):
    def node(state):
        s = _to_state(state)
        return evaluator(s)

    return node


def _make_supervisor_node(supervisor):
    def node(state):
        s = _to_state(state)
        result = supervisor(s)
        # 强制返回 Command，确保状态更新生效
        from src.state import RoutingFlag

        if result.get("routing_flag") == RoutingFlag.END:
            return Command(
                goto="router",
                update={
                    "routing_flag": RoutingFlag.END,
                    "human_intervened": True,
                },
            )
        elif result.get("routing_flag") == RoutingFlag.CONTINUE:
            return Command(
                goto="router",
                update={
                    "routing_flag": RoutingFlag.CONTINUE,
                    "human_intervened": True,
                    "current_topic_id": result.get("current_topic_id"),
                    "current_topic_index": result.get("current_topic_index"),
                },
            )
        return Command(goto="router", update=result)

    return node


def _make_reporting_node():
    def node(state):
        s = _to_state(state)

        records = []
        for rec in s.evaluation_records:
            if isinstance(rec, dict):
                records.append(rec)
            else:
                records.append(rec.model_dump())

        plan_dicts = [_to_dict(t) for t in s.interview_plan]
        report = generate_report(records, plan_dicts)
        return {"report": report, "routing_flag": RoutingFlag.END}

    return node


def _make_router_node(mock_sigma: float | None = None, force_consecutive_medium: int = 0):
    def node(state):
        s = _to_state(state)

        if force_consecutive_medium > 0:
            _counters.consecutive_medium = force_consecutive_medium

        # 如果人工已干预，直接按 routing_flag 路由
        if s.human_intervened:
            if s.routing_flag in (RoutingFlag.CONTINUE, RoutingFlag.RETRY):
                return {"next_node": "questioner"}
            else:
                # 人工 END 时标记当前议题已完成
                plan = [_to_dict(t) for t in s.interview_plan]
                for t in plan:
                    if t["topic_id"] == s.current_topic_id:
                        t["status"] = "completed"
                        break
                return {"interview_plan": plan, "next_node": "reporting"}

        records = s.evaluation_records
        if records:
            scores = [r["score"] if isinstance(r, dict) else r.score for r in records[-3:]]
            sigma = mock_sigma if mock_sigma is not None else calculate_std(scores)
        else:
            sigma = 3.0

        plan_dicts = [_to_dict(t) for t in s.interview_plan]
        decision = route_next_node(
            sigma=sigma,
            counters=_counters,
            interview_plan=plan_dicts,
            current_topic_id=s.current_topic_id,
            current_topic_index=s.current_topic_index,
        )

        updates: dict = {}

        if decision == RoutingDecision.QUESTIONER:
            update_dict, next_node = _advance_topic(s)
            updates.update(update_dict)
            updates["next_node"] = next_node
        elif decision == RoutingDecision.REPORTING:
            # 标记当前议题已完成
            plan = [_to_dict(t) for t in s.interview_plan]
            for t in plan:
                if t["topic_id"] == s.current_topic_id:
                    t["status"] = "completed"
                    break
            updates["interview_plan"] = plan
            updates["next_node"] = "reporting"
        elif decision == RoutingDecision.SUPERVISOR:
            updates["next_node"] = "supervisor"
        else:
            # UNKNOWN 也标记当前议题完成再结束
            plan = [_to_dict(t) for t in s.interview_plan]
            for t in plan:
                if t["topic_id"] == s.current_topic_id:
                    t["status"] = "completed"
                    break
            updates["interview_plan"] = plan
            updates["next_node"] = "reporting"

        return updates

    return node


def _setup_signal_handler(graph):
    def handler(signum, frame):
        snapshot_path = f"./state_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(snapshot_path, "w") as f:
                json.dump({"signal": signum, "timestamp": datetime.now().isoformat()}, f)
        except Exception:
            pass

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
