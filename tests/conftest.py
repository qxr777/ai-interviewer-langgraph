"""Pytest 全局 fixtures：所有测试共用的 mock 数据和工具。"""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_global_counters():
    """每个测试前重置全局计数器。"""
    try:
        from src.graph.builder import _counters

        _counters.retry_counts.clear()
        _counters.global_round_count = 0
        _counters.consecutive_medium = 0
        _counters.invalid_input_count = 0
        _counters.current_topic = None
        if hasattr(_counters, "_records"):
            _counters._records.clear()
    except ImportError:
        pass  # 模块尚未加载，跳过


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def mock_resume_path(fixtures_dir):
    """模拟简历 PDF 路径。"""
    return str(fixtures_dir / "mock_resume.pdf")


@pytest.fixture
def sample_state_data(fixtures_dir):
    """从 sample_state.json 加载预填充状态。"""
    with open(fixtures_dir / "sample_state.json") as f:
        return json.load(f)


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 返回的文本响应。"""
    return "这是一个模拟的 AI 回答。"


@pytest.fixture
def mock_interview_plan():
    """模拟面试大纲（3 个议题）。"""
    return [
        {"topic_id": "topic_1", "topic_name": "Python 基础", "status": "pending"},
        {"topic_id": "topic_2", "topic_name": "系统设计", "status": "pending"},
        {"topic_id": "topic_3", "topic_name": "数据库优化", "status": "pending"},
    ]


@pytest.fixture
def mock_evaluation_scores():
    """模拟 3 个评估官的评分。"""
    return [
        {
            "score": 82,
            "topic_id": "topic_1",
            "rationale": (
                "候选人展示了扎实的 Python 基础，能够清晰解释装饰器的工作原理，"
                "并在回答中提到了实际项目中的应用场景。整体表现良好。"
            ),
        },
        {
            "score": 78,
            "topic_id": "topic_1",
            "rationale": "回答内容基本正确，对装饰器的理解到位，但在高级特性如参数化装饰器方面略有欠缺。总体表现合格。",
        },
        {
            "score": 85,
            "topic_id": "topic_1",
            "rationale": (
                "候选人对 Python 装饰器有深入理解，不仅回答了基础概念，还主动提到了 functools.wraps 的细节，表现优秀。"
            ),
        },
    ]


@pytest.fixture
def candidate_info_clean():
    """已脱敏的候选人信息。"""
    return {
        "name": "张三",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "experience_years": 5,
        "education": "本科 - 计算机科学",
    }


@pytest.fixture
def job_description():
    """岗位描述。"""
    return "Senior Python Developer - 需要 5 年以上后端开发经验，精通 FastAPI 和分布式系统设计。"
