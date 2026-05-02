"""REST API 路由。"""

import base64
import os
import tempfile
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.sessions import interview_sessions
from src.config import load_config
from src.graph.builder import build_interview_graph
from src.state import InterviewState, RoutingFlag

router = APIRouter()


class StartInterviewRequest(BaseModel):
    resume_file: str  # base64 encoded PDF/DOCX
    job_description: str


class AnswerRequest(BaseModel):
    answer: str


class ArbitrateRequest(BaseModel):
    action: str


@router.post("/start")
async def start_interview(req: StartInterviewRequest):
    interview_id = str(uuid.uuid4())

    # Decode resume
    try:
        file_bytes = base64.b64decode(req.resume_file)
    except Exception:
        raise HTTPException(status_code=400, detail="简历文件编码无效") from None

    from src.tools.resume_parser import parse_resume_document

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
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
    state.chat_history.append(ChatMessage(
        role="candidate",
        content=req.answer,
        topic_id=state.current_topic_id,
    ))

    state_dict = state.model_dump()
    config = {"configurable": {"thread_id": interview_id}}
    result = graph.invoke(state_dict, config)

    session["state"] = InterviewState(**result)

    updated = InterviewState(**result)

    ai_message = None
    scores = []
    prev_count = len(state.evaluation_records)
    new_records = result.get("evaluation_records", [])[prev_count:]

    for msg in reversed(result.get("chat_history", [])):
        if isinstance(msg, dict):
            if msg.get("role") == "ai":
                ai_message = msg["content"]
                break
        else:
            if msg.role == "ai":
                ai_message = msg.content
                break

    for rec in new_records:
        if isinstance(rec, dict):
            scores.append({"score": rec["score"], "rationale": rec["rationale"], "topic_id": rec["topic_id"]})
        else:
            scores.append({"score": rec.score, "rationale": rec.rationale, "topic_id": rec.topic_id})

    # 检测评分分歧：σ > 15.0 触发人工仲裁
    import math
    from src.graph.governance import calculate_std
    routing_flag = updated.routing_flag.value if hasattr(updated.routing_flag, "value") else updated.routing_flag
    if scores:
        score_values = [s["score"] for s in scores]
        sigma = calculate_std(score_values)
        if sigma > 15.0:
            session["state"].routing_flag = RoutingFlag.ESCALATE
            routing_flag = RoutingFlag.ESCALATE.value

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
        "chat_count": len(state.chat_history),
    }


@router.get("/{interview_id}/report")
async def get_report(interview_id: str):
    if interview_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="面试不存在")

    session = interview_sessions[interview_id]
    state = session["state"]
    return state.report or {"status": "no_valid_evaluations", "topics": []}
