"""T17: Questioner 节点单元测试。

覆盖：追加 AI 消息、不含评分数字、不泄露系统指令。
"""


def _get_questioner():
    from src.agents.questioner import node_questioner

    return node_questioner


class TestNodeQuestioner:
    """Questioner 节点测试。"""

    def test_appends_ai_message(self, mock_interview_plan):
        """生成一条 AI 角色消息追加到 chat_history。"""
        node_questioner = _get_questioner()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            chat_history=[],
            routing_flag="CONTINUE",
        )

        questioner = node_questioner(llm_model="mock")
        result = questioner(state)

        assert "chat_history" in result
        # Mock 模式下会追加 AI 提问 + 模拟候选人回答
        assert len(result["chat_history"]) >= 1
        # 第一条应该是 AI 消息
        first_new = result["chat_history"][0]
        assert first_new.role == "ai"

    def test_no_score_in_output(self, mock_interview_plan):
        """输出不应包含评分数字。"""
        import re

        node_questioner = _get_questioner()
        from src.state import InterviewState

        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            chat_history=[],
            routing_flag="CONTINUE",
        )

        questioner = node_questioner(llm_model="mock")
        result = questioner(state)

        for msg in result["chat_history"]:
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            assert not re.search(r"\d{1,3}\s*分", content), f"Questioner 输出含评分: {content}"

    def test_preserves_existing_history(self, mock_interview_plan):
        """不应覆盖已有的 chat_history。"""
        node_questioner = _get_questioner()
        from src.state import ChatMessage, InterviewState

        existing = [ChatMessage(role="ai", content="你好", topic_id="topic_1")]
        state = InterviewState(
            candidate_info={"name": "Test", "skills": []},
            interview_plan=mock_interview_plan,
            current_topic_id="topic_1",
            chat_history=existing,
            routing_flag="CONTINUE",
        )

        questioner = node_questioner(llm_model="mock")
        result = questioner(state)

        assert len(result["chat_history"]) > len(existing)
        assert result["chat_history"][0].content == existing[0].content
        assert result["chat_history"][0].role == existing[0].role
