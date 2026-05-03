"""评估工具：submit_evaluation 工具 + 参数校验。"""

from pydantic import BaseModel, Field, ValidationError


class EvaluationInput(BaseModel):
    """评估输入校验模型。"""

    score: int = Field(ge=1, le=100, description="评分，1-100 之间的整数")
    topic_id: str = Field(min_length=1, description="议题 ID")
    rationale: str = Field(min_length=50, description="评判理据，不少于 50 字")


def submit_evaluation(score: int, topic_id: str, rationale: str) -> dict:
    """提交单次考核成绩的唯一入口。

    Args:
        score: 1-100 之间的整数。
        topic_id: 必须匹配 current_topic_id。
        rationale: 字符串长度 ≥ 50。

    Returns:
        结构化的评估记录字典。

    Raises:
        ValidationError: 参数校验失败时抛出。
    """
    try:
        validated = EvaluationInput(score=score, topic_id=topic_id, rationale=rationale)
    except ValidationError as e:
        raise ValueError(f"评估参数校验失败: {e}") from e

    return {
        "score": validated.score,
        "topic_id": validated.topic_id,
        "rationale": validated.rationale,
    }
