"""Node_Human_Supervisor：人工断点挂起/恢复。"""

from src.state import InterviewState, RoutingFlag


class NodeHumanSupervisor:
    """人工仲裁者节点。

    挂起系统流转，等待外部输入干预指令。
    """

    def __init__(self, llm_model: str = "", mock_input: str | None = None):
        self.mock_input = mock_input

    def __call__(self, state: InterviewState) -> dict:
        if self.mock_input is not None:
            action = self.mock_input
        else:
            topic_name = self._get_topic_name(state)
            print(f"\n{'=' * 60}")
            print("⚠  系统已挂起，等待人工仲裁")
            print(f"当前议题: {topic_name}")
            print("操作: CONTINUE (继续) / SKIP (跳过) / END (结束)")
            print(f"{'=' * 60}")
            action = input("请输入操作指令: ").strip().upper()

        if action == "CONTINUE":
            return {"routing_flag": RoutingFlag.CONTINUE, "human_intervened": True}
        elif action == "SKIP":
            next_idx = state.current_topic_index + 1
            if next_idx < len(state.interview_plan):
                new_topic = state.interview_plan[next_idx]
                return {
                    "routing_flag": RoutingFlag.CONTINUE,
                    "current_topic_id": new_topic.topic_id,
                    "current_topic_index": next_idx,
                    "human_intervened": True,
                }
            else:
                return {"routing_flag": RoutingFlag.END}
        elif action == "END":
            return {"routing_flag": RoutingFlag.END}
        else:
            print(f"未知指令: {action}，请重新输入")
            return self(state)

    def _get_topic_name(self, state: InterviewState) -> str:
        for topic in state.interview_plan:
            if topic.topic_id == state.current_topic_id:
                return topic.topic_name
        return "未知"
