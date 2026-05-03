"""SSE 流式端点。"""

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.sessions import interview_sessions

sse_router = APIRouter()


@sse_router.get("/{interview_id}/stream")
async def stream_events(interview_id: str):
    if interview_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="面试不存在")

    async def event_generator():
        session = interview_sessions[interview_id]
        state = session["state"]
        queue: asyncio.Queue = session.get("event_queue")

        # 推送当前状态
        flag = state.routing_flag.value if hasattr(state.routing_flag, "value") else state.routing_flag
        yield f"data: {json.dumps({'type': 'status', 'flag': flag}, ensure_ascii=False)}\n\n"

        # 推送历史消息
        for msg in state.chat_history:
            msg_dict = msg if isinstance(msg, dict) else msg.model_dump()
            yield f"data: {json.dumps({'type': 'message', **msg_dict}, ensure_ascii=False)}\n\n"

        # 从队列读取实时事件
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except TimeoutError:
                # 超时发送心跳保持连接
                yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
