"""补充：报告生成测试。

覆盖：有效成绩汇总、空报告处理、平均分计算。
"""

import pytest


def _get_report_generator():
    from src.graph.builder import generate_report
    return generate_report


class TestReportGeneration:
    """报告生成测试。"""

    def test_report_with_scores(self):
        """有效成绩 → 含平均分和议题详情。"""
        generate_report = _get_report_generator()
        evaluation_records = [
            {"score": 80, "topic_id": "topic_1", "rationale": "候选人表现良好，回答准确且条理清晰。"},
            {"score": 82, "topic_id": "topic_1", "rationale": "候选人基础扎实，对核心概念理解到位。"},
            {"score": 78, "topic_id": "topic_1", "rationale": "候选人回答基本正确，部分细节有待加强。"},
            {"score": 90, "topic_id": "topic_2", "rationale": "候选人展示了出色的系统设计能力，方案全面。"},
            {"score": 88, "topic_id": "topic_2", "rationale": "设计思路清晰，考虑了可扩展性和性能因素。"},
            {"score": 85, "topic_id": "topic_2", "rationale": "整体方案合理，在容错处理方面有独到见解。"},
        ]
        interview_plan = [
            {"topic_id": "topic_1", "topic_name": "Python 基础", "status": "completed"},
            {"topic_id": "topic_2", "topic_name": "系统设计", "status": "completed"},
            {"topic_id": "topic_3", "topic_name": "数据库", "status": "pending"},
        ]

        report = generate_report(evaluation_records, interview_plan)

        assert "topics" in report
        # topic_1 平均分应为 80
        topic1 = [t for t in report["topics"] if t["topic_id"] == "topic_1"][0]
        assert abs(topic1["average_score"] - 80.0) < 0.01

    def test_empty_report(self):
        """无有效成绩 → status: no_valid_evaluations。"""
        generate_report = _get_report_generator()

        report = generate_report([], [
            {"topic_id": "topic_1", "topic_name": "A", "status": "pending"},
        ])

        assert report["status"] == "no_valid_evaluations"

    def test_report_json_serializable(self):
        """报告应可序列化为 JSON。"""
        import json
        generate_report = _get_report_generator()

        report = generate_report([
            {"score": 80, "topic_id": "topic_1", "rationale": "x" * 50},
        ], [
            {"topic_id": "topic_1", "topic_name": "A", "status": "completed"},
        ])

        # 不应抛异常
        json.dumps(report)
