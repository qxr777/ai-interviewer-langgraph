"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.api.sessions import interview_sessions
from src.api.sse import sse_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # 优雅关闭：清理会话
    interview_sessions.clear()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Interviewer API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载路由
    app.include_router(router, prefix="/interview", tags=["interview"])
    app.include_router(sse_router, prefix="/interview", tags=["sse"])

    return app
