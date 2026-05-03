"""T08: Prompts 模板测试。

覆盖：模板渲染正确、含 anti-injection 指令、Questioner 不含评分词汇。
"""

import re


def _get_prompts():
    from src.utils.prompts import (
        EVALUATOR_PROMPT,
        PLANNER_PROMPT,
        QUESTIONER_PROMPT,
        SUPERVISOR_PROMPT,
    )

    return PLANNER_PROMPT, QUESTIONER_PROMPT, EVALUATOR_PROMPT, SUPERVISOR_PROMPT


class TestPromptTemplatesExist:
    """所有角色模板必须定义。"""

    def test_planner_prompt(self):
        planner_prompt = _get_prompts()[0]
        assert "简历" in planner_prompt or "resume" in planner_prompt.lower()

    def test_questioner_prompt(self):
        questioner_prompt = _get_prompts()[1]
        assert len(questioner_prompt) > 0

    def test_evaluator_prompt(self):
        evaluator_prompt = _get_prompts()[2]
        assert len(evaluator_prompt) > 0

    def test_supervisor_prompt(self):
        supervisor_prompt = _get_prompts()[3]
        assert len(supervisor_prompt) > 0


class TestAntiInjection:
    """元指令禁止层：所有角色模板应含防注入指令。"""

    def test_planner_has_anti_injection(self):
        planner_prompt = _get_prompts()[0]
        assert "禁止" in planner_prompt or "不要" in planner_prompt or "system" in planner_prompt.lower()

    def test_questioner_has_anti_injection(self):
        questioner_prompt = _get_prompts()[1]
        assert "禁止" in questioner_prompt or "不要" in questioner_prompt or "system" in questioner_prompt.lower()

    def test_evaluator_has_anti_injection(self):
        evaluator_prompt = _get_prompts()[2]
        assert "禁止" in evaluator_prompt or "不要" in evaluator_prompt or "system" in evaluator_prompt.lower()


class TestQuestionerNoScoring:
    """Questioner prompt 不应包含评分/打分相关词汇。"""

    def test_no_scoring_words(self):
        questioner_prompt = _get_prompts()[1]
        lower = questioner_prompt.lower()
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
        evaluator_prompt = _get_prompts()[2]
        assert "score" in evaluator_prompt.lower() or "分数" in evaluator_prompt

    def test_requires_rationale(self):
        evaluator_prompt = _get_prompts()[2]
        assert "rationale" in evaluator_prompt.lower() or "理据" in evaluator_prompt or "理由" in evaluator_prompt


class TestPromptVariableSubstitution:
    """模板变量替换测试。"""

    def test_planner_accepts_candidate_and_jd(self):
        planner_prompt = _get_prompts()[0]
        assert "{candidate_info}" in planner_prompt or "candidate" in planner_prompt.lower()
        assert "{job_description}" in planner_prompt or "job_description" in planner_prompt.lower()

    def test_questioner_accepts_topic_and_history(self):
        questioner_prompt = _get_prompts()[1]
        assert "topic" in questioner_prompt.lower() or "{topic}" in questioner_prompt
        assert "history" in questioner_prompt.lower() or "{history}" in questioner_prompt
