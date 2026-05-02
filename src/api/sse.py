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

        yield f"data: {json.dumps({'type': 'status', 'flag': state.routing_flag.value}, ensure_ascii=False)}\n\n"

        for msg in state.chat_history:
            msg_dict = msg if isinstance(msg, dict) else msg.model_dump()
            yield f"data: {json.dumps({'type': 'message', **msg_dict}, ensure_ascii=False)}\n\n"

        while True:
            yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(30)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
