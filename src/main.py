"""CLI 入口：启动图执行、处理候选人终端输入、输出最终面试报告。"""

import argparse
import json

from src.config import load_config
from src.graph.builder import build_interview_graph
from src.state import InterviewState, RoutingFlag


def main():
    parser = argparse.ArgumentParser(description="AI 智能面试官自治系统")
    parser.add_argument("--resume", required=False, help="简历文件路径 (PDF/Word)")
    parser.add_argument("--jd", required=False, help="岗位描述")
    parser.add_argument("--language", default="zh", help="面试语言 (默认: zh)")
    parser.add_argument("--mock", action="store_true", help="使用模拟 LLM 模式")
    args = parser.parse_args()

    config = load_config()

    # 解析简历
    candidate_info = (
        _parse_resume(args.resume)
        if args.resume
        else {
            "name": "匿名候选人",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience_years": 5,
        }
    )

    job_description = args.jd or "Senior Python Developer"

    # 构建图
    use_mock = args.mock or not config.get("llm_api_key")
    graph = build_interview_graph(
        llm_model="mock" if use_mock else config["llm_model"],
        job_description=job_description,
        evaluator_count=config["evaluator_count"],
        use_mock=use_mock,
    )

    # 初始化状态
    initial_state = InterviewState(
        candidate_info=candidate_info,
        routing_flag=RoutingFlag.CONTINUE,
    )

    print(f"\n{'=' * 60}")
    print("🚀 AI 智能面试官启动")
    print(f"候选人: {candidate_info.get('name', '未知')}")
    print(f"岗位: {job_description}")
    print(f"{'=' * 60}\n")

    # 执行图
    import uuid

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(initial_state, config)

    # 输出报告
    if result.get("report"):
        print(f"\n{'=' * 60}")
        print("📋 面试报告")
        print(f"{'=' * 60}")
        print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    else:
        print("\n面试结束，未生成报告。")


def _parse_resume(resume_path: str | None) -> dict:
    if not resume_path:
        return {}
    from src.tools.resume_parser import parse_resume_document

    try:
        return parse_resume_document(resume_path)
    except Exception as e:
        print(f"⚠ 简历解析失败: {e}，使用默认信息")
        return {"name": "解析失败", "skills": [], "experience_years": 0}


if __name__ == "__main__":
    main()
