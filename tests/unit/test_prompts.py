"""T08: Prompts 模板测试。

覆盖：模板渲染正确、含 anti-injection 指令、Questioner 不含评分词汇。
"""

import re
import pytest


def _get_prompts():
    from src.utils.prompts import (
        PLANNER_PROMPT,
        QUESTIONER_PROMPT,
        EVALUATOR_PROMPT,
        SUPERVISOR_PROMPT,
    )
    return PLANNER_PROMPT, QUESTIONER_PROMPT, EVALUATOR_PROMPT, SUPERVISOR_PROMPT


class TestPromptTemplatesExist:
    """所有角色模板必须定义。"""

    def test_planner_prompt(self):
        PLANNER_PROMPT = _get_prompts()[0]
        assert "简历" in PLANNER_PROMPT or "resume" in PLANNER_PROMPT.lower()

    def test_questioner_prompt(self):
        QUESTIONER_PROMPT = _get_prompts()[1]
        assert len(QUESTIONER_PROMPT) > 0

    def test_evaluator_prompt(self):
        EVALUATOR_PROMPT = _get_prompts()[2]
        assert len(EVALUATOR_PROMPT) > 0

    def test_supervisor_prompt(self):
        SUPERVISOR_PROMPT = _get_prompts()[3]
        assert len(SUPERVISOR_PROMPT) > 0


class TestAntiInjection:
    """元指令禁止层：所有角色模板应含防注入指令。"""

    def test_planner_has_anti_injection(self):
        PLANNER_PROMPT = _get_prompts()[0]
        assert "禁止" in PLANNER_PROMPT or "不要" in PLANNER_PROMPT or "system" in PLANNER_PROMPT.lower()

    def test_questioner_has_anti_injection(self):
        QUESTIONER_PROMPT = _get_prompts()[1]
        assert "禁止" in QUESTIONER_PROMPT or "不要" in QUESTIONER_PROMPT or "system" in QUESTIONER_PROMPT.lower()

    def test_evaluator_has_anti_injection(self):
        EVALUATOR_PROMPT = _get_prompts()[2]
        assert "禁止" in EVALUATOR_PROMPT or "不要" in EVALUATOR_PROMPT or "system" in EVALUATOR_PROMPT.lower()


class TestQuestionerNoScoring:
    """Questioner prompt 不应包含评分/打分相关词汇。"""

    def test_no_scoring_words(self):
        QUESTIONER_PROMPT = _get_prompts()[1]
        lower = QUESTIONER_PROMPT.lower()
        # 检查具体的评分泄露模式，不是单个字
        scoring_patterns = [
            r"score\s*[:：]\s*\d",
            r"得\s*\d+\s*分",
            r"\d{1,3}\s*分",
            r"grading",
        ]
        for pattern in scoring_patterns:
            assert not re.search(pattern, lower), f"Questioner prompt 不应包含评分模式: {pattern}"


class TestEvaluatorStructuredOutput:
    """Evaluator prompt 应要求结构化评分输出。"""

    def test_requires_score(self):
        EVALUATOR_PROMPT = _get_prompts()[2]
        assert "score" in EVALUATOR_PROMPT.lower() or "分数" in EVALUATOR_PROMPT

    def test_requires_rationale(self):
        EVALUATOR_PROMPT = _get_prompts()[2]
        assert "rationale" in EVALUATOR_PROMPT.lower() or "理据" in EVALUATOR_PROMPT or "理由" in EVALUATOR_PROMPT


class TestPromptVariableSubstitution:
    """模板变量替换测试。"""

    def test_planner_accepts_candidate_and_jd(self):
        PLANNER_PROMPT = _get_prompts()[0]
        assert "{candidate_info}" in PLANNER_PROMPT or "candidate" in PLANNER_PROMPT.lower()
        assert "{job_description}" in PLANNER_PROMPT or "job_description" in PLANNER_PROMPT.lower()

    def test_questioner_accepts_topic_and_history(self):
        QUESTIONER_PROMPT = _get_prompts()[1]
        assert "topic" in QUESTIONER_PROMPT.lower() or "{topic}" in QUESTIONER_PROMPT
        assert "history" in QUESTIONER_PROMPT.lower() or "{history}" in QUESTIONER_PROMPT
