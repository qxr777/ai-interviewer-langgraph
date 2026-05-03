"""REST API 路由。"""

import asyncio
import base64
import os
import tempfile
import uuid
import base64
import os
import tempfile
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.sessions import interview_sessions
from src.config import load_config
from src.graph.builder import build_interview_graph, generate_report
from src.graph.governance import calculate_std
from src.state import InterviewState, RoutingFlag

router = APIRouter()


class StartInterviewRequest(BaseModel):
    resume_file: str  # base64 encoded PDF/DOCX
    job_description: str


class AnswerRequest(BaseModel):
    answer: str


class ArbitrateRequest(BaseModel):
    action: str


async def _push_event(interview_id: str, event: dict):
    """推送 SSE 事件到 session 队列。"""
    session = interview_sessions.get(interview_id)
    if session and "event_queue" in session:
        await session["event_queue"].put(event)


@router.post("/start")
async def start_interview(req: StartInterviewRequest):
    interview_id = str(uuid.uuid4())

    # Decode resume
    try:
        file_bytes = base64.b64decode(req.resume_file)
    except Exception:
        raise HTTPException(status_code=400, detail="简历文件编码无效") from None

    from src.tools.resume_parser import parse_resume_document

    # Detect file type from magic bytes
    if file_bytes[:2] == b'PK':
        suffix = '.docx'
    elif file_bytes[:4] == b'%PDF':
        suffix = '.pdf'
    else:
        suffix = '.docx'  # fallback

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        candidate_info = parse_resume_document(tmp_path)
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=400, detail=f"简历解析失败: {e}") from e

    os.unlink(tmp_path)

    config = load_config()
    use_mock = not config.get("llm_api_key")

    graph = build_interview_graph(
        llm_model="mock" if use_mock else config.get("llm_model", "deepseek-chat"),
        job_description=req.job_description,
        evaluator_count=config["evaluator_count"],
        use_mock=use_mock,
    )

    # Step 1: Run planner to create topics
    from src.agents.planner import NodePlanner
    planner = NodePlanner(
        llm_model="mock" if use_mock else config.get("llm_model", "deepseek-chat"),
        job_description=req.job_description,
        use_mock=use_mock,
    )

    initial_state = InterviewState(
        candidate_info=candidate_info,
        routing_flag=RoutingFlag.CONTINUE,
    )

    plan_result = planner(initial_state)
    plan_items = plan_result["interview_plan"]
    first_tid = plan_items[0]["topic_id"] if isinstance(plan_items[0], dict) else plan_items[0].topic_id

    # Step 2: Run questioner only (no evaluation yet)
    from src.agents.questioner import NodeQuestioner
    questioner = NodeQuestioner(
        llm_model="mock" if use_mock else config.get("llm_model", "deepseek-chat"),
        use_mock=use_mock,
    )

    planned_state = InterviewState(
        candidate_info=candidate_info,
        interview_plan=plan_items,
        current_topic_id=first_tid,
        current_topic_index=0,
        routing_flag=RoutingFlag.CONTINUE,
        next_node="questioner",
    )

    question_result = questioner(planned_state)

    # Build state with plan + first question
    started_state = InterviewState(
        candidate_info=candidate_info,
        interview_plan=plan_result["interview_plan"],
        chat_history=question_result["chat_history"],
        current_topic_id=first_tid,
        current_topic_index=0,
        routing_flag=RoutingFlag.CONTINUE,
        next_node="questioner",
    )

    interview_sessions[interview_id] = {
        "graph": graph,
        "state": started_state,
        "event_queue": asyncio.Queue(),
    }

    # 提取第一条 AI 提问
    ai_message = None
    for msg in started_state.chat_history:
        if msg.role == "ai":
            ai_message = msg.content
            break

    return {
        "interview_id": interview_id,
        "status": "started",
        "ai_response": ai_message,
        "interview_plan": [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in started_state.interview_plan
        ],
        "current_topic_id": started_state.current_topic_id,
    }


@router.post("/{interview_id}/answer")
async def submit_answer(interview_id: str, req: AnswerRequest):
    if interview_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="面试不存在")

    session = interview_sessions[interview_id]
    state = session["state"]
    graph = session["graph"]

    from src.state import ChatMessage
    new_msg = ChatMessage(
        role="candidate",
        content=req.answer,
        topic_id=state.current_topic_id,
    )

    config = {"configurable": {"thread_id": interview_id}}

    # 从 checkpoint 获取累计的评分数量
    prev_snapshot = graph.get_state(config)
    prev_count = len(prev_snapshot.values.get("evaluation_records", []))

    # 只传递变更的字段：chat_history 仅传新消息（由 reducer 累加），evaluation_records 置空
    state_dict = state.model_dump()
    state_dict["chat_history"] = [new_msg.model_dump()]
    state_dict["evaluation_records"] = []

    ai_message = None

    # SSE: 推送开始处理状态
    await _push_event(interview_id, {"type": "status", "flag": "processing"})

    # 使用 astream 逐节点推送 SSE 事件
    async for event in graph.astream(state_dict, config):
        for node_name, update in event.items():
            if node_name == "questioner" and isinstance(update, dict):
                chat_updates = update.get("chat_history", [])
                for msg in chat_updates:
                    role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
                    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                    if role == "ai" and content:
                        ai_message = content
                        await _push_event(interview_id, {
                            "type": "message",
                            "role": "ai",
                            "content": content,
                        })
            elif node_name == "router" and isinstance(update, dict):
                next_node = update.get("next_node", "")
                flag_map = {
                    "questioner": "CONTINUE",
                    "supervisor": "ESCALATE",
                    "reporting": "END",
                }
                flag = flag_map.get(next_node)
                if flag:
                    await _push_event(interview_id, {"type": "status", "flag": flag})
            elif node_name == "evaluator":
                await _push_event(interview_id, {"type": "status", "flag": "evaluating"})

    # 从 checkpoint 读取最终状态（reducer 已在 astream 内部应用）
    checkpoint = graph.get_state(config)
    updated = InterviewState(**checkpoint.values)
    session["state"] = updated

    # 提取评分
    scores = []
    new_records = updated.evaluation_records[prev_count:]
    for rec in new_records:
        if isinstance(rec, dict):
            scores.append({"score": rec["score"], "rationale": rec["rationale"], "topic_id": rec["topic_id"]})
        else:
            scores.append({"score": rec.score, "rationale": rec.rationale, "topic_id": rec.topic_id})

    # 检测评分分歧
    routing_flag = updated.routing_flag.value if hasattr(updated.routing_flag, "value") else updated.routing_flag
    if scores:
        score_values = [s["score"] for s in scores]
        sigma = calculate_std(score_values)
        if sigma > 15.0:
            session["state"].routing_flag = RoutingFlag.ESCALATE
            routing_flag = RoutingFlag.ESCALATE.value
            await _push_event(interview_id, {"type": "status", "flag": "ESCALATE"})

    if not ai_message:
        for msg in reversed(updated.chat_history):
            if isinstance(msg, dict):
                if msg.get("role") == "ai":
                    ai_message = msg["content"]
                    break
            else:
                if msg.role == "ai":
                    ai_message = msg.content
                    break

    return {
        "ai_response": ai_message,
        "scores": scores,
        "interview_plan": [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in updated.interview_plan
        ],
        "current_topic_id": updated.current_topic_id,
        "routing_flag": routing_flag,
        "status": "ok",
    }


@router.post("/{interview_id}/arbitrate")
async def arbitrate(interview_id: str, req: ArbitrateRequest):
    if interview_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="面试不存在")

    session = interview_sessions[interview_id]
    state = session["state"]

    if req.action == "CONTINUE":
        state.routing_flag = RoutingFlag.CONTINUE
    elif req.action == "SKIP":
        state.routing_flag = RoutingFlag.CONTINUE
        state.current_topic_index += 1
    elif req.action == "END":
        state.routing_flag = RoutingFlag.END

    await _push_event(interview_id, {"type": "status", "flag": req.action})
    session["state"] = state
    return {"status": "ok", "action": req.action}


@router.get("/{interview_id}/status")
async def get_status(interview_id: str):
    if interview_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="面试不存在")

    session = interview_sessions[interview_id]
    state = session["state"]
    return {
        "routing_flag": state.routing_flag.value if hasattr(state.routing_flag, "value") else state.routing_flag,
        "current_topic_id": state.current_topic_id,
        "current_topic_index": state.current_topic_index,
        "chat_history": [m.model_dump() if hasattr(m, "model_dump") else m for m in state.chat_history],
        "interview_plan": [t.model_dump() if hasattr(t, "model_dump") else t for t in state.interview_plan],
        "chat_count": len(state.chat_history),
    }


@router.get("/{interview_id}/report")
async def get_report(interview_id: str):
    if interview_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="面试不存在")

    session = interview_sessions[interview_id]
    state = session["state"]

    if state.report:
        return state.report

    # 面试未结束，从 session 内存状态读取评估记录生成临时报告
    # （ANSWER 端点会在 astream 完成后更新 session["state"]）
    records = []
    for rec in state.evaluation_records:
        if isinstance(rec, dict):
            records.append(rec)
        else:
            records.append(rec.model_dump())

    plan_dicts = [t.model_dump() if hasattr(t, "model_dump") else t for t in state.interview_plan]
    return generate_report(records, plan_dicts)
