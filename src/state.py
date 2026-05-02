"""InterviewState 数据模型和路由状态枚举。"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RoutingFlag(str, Enum):
    """决定图流转方向的全局信号灯。"""
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    ESCALATE = "ESCALATE"
    END = "END"


class TopicItem(BaseModel):
    """面试议题。"""
    topic_id: str
    topic_name: str
    status: str = "pending"  # pending / in_progress / completed


class ChatMessage(BaseModel):
    """对话消息。"""
    role: str  # system / ai / candidate
    content: str
    topic_id: str | None = None


class EvaluationRecord(BaseModel):
    """评估记录。"""
    score: int = Field(ge=1, le=100)
    topic_id: str
    rationale: str


class InterviewState(BaseModel):
    """全局共享的状态对象。"""
    candidate_info: dict[str, Any]
    interview_plan: list[TopicItem] = Field(default_factory=list)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    current_topic_id: str | None = None
    current_topic_index: int = 0
    evaluation_records: list[EvaluationRecord] = Field(default_factory=list)
    routing_flag: RoutingFlag

    # 报告（由 REPORTING 节点写入）
    report: dict[str, Any] | None = None

    # 内部路由目标（用于条件边）
    next_node: str = "questioner"

    # 人工干预标记（防止重复触发 ESCALATE）
    human_intervened: bool = False
