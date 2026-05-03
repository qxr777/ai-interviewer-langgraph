# Harness Engineering 设计文档

## 什么是 Harness

在本系统中，**Harness 是包裹在非确定性 LLM Agent 外面的确定性控制层**。它将系统的流转规则收敛为严格的状态机，确保任何路径都不会偏离边界。

LLM 节点（Planner、Questioner、Evaluator）的输出是不可预测的——同一输入可能产生不同结果。Harness 的职责是：**允许 LLM 自由生成内容，但由确定性代码决定系统的下一步走向。**

## 架构：确定性 vs 非确定性分离

```
┌─────────────────────────────────────────────────────────┐
│                    Harness（确定性）                       │
│                                                         │
│  governance.py  →  σ 计算 / 计数器管理 / 置信度判定       │
│  router.py      →  if-elif 路由决策                      │
│  builder.py     →  状态机拓扑 / 条件边 / 持久化            │
│  state.py       →  RoutingFlag 枚举 / InterviewState     │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              LLM Agent（非确定性）                    │  │
│  │  planner.py  →  议题规划                            │  │
│  │  questioner.py →  智能提问                          │  │
│  │  evaluator.py  →  多路评分                          │  │
│  │  supervisor.py →  人工仲裁                          │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Agent 输出数据 → Harness 测量指标 → Harness 决定下一节点  │
└─────────────────────────────────────────────────────────┘
```

**关键原则**：LLM 节点只写入数据，不参与任何路由决策。路由由 σ 和计数器这些**可测量、可复现**的指标决定。

## 1. 状态机边界约束

Harness 通过 `RoutingFlag` 枚举强制限定所有可能的流转方向：

```python
class RoutingFlag(StrEnum):
    CONTINUE = "CONTINUE"   # 高置信度 → 下一议题
    RETRY = "RETRY"         # 中置信度 → 重试
    ESCALATE = "ESCALATE"   # 低置信度 → 人工仲裁
    END = "END"             # 结束面试
```

LLM 节点**不能自己决定下一步**，只能返回数据。Harness 的 `router.py` 根据 σ 区间和计数器状态选择唯一路径，覆盖状态转换表的全部规则。

## 2. 治理指标驱动决策

Harness 不依赖 LLM 的"自我评估"，而是用可测量的统计指标做决策：

### σ 标准差分析

3 路评估官独立打分后，Harness 计算标准差 σ：

| σ 区间 | 定性 | 动作 |
|--------|------|------|
| σ ≤ 5.0 | 高置信度 | 记录平均分，流转至下一议题 |
| 5.0 < σ ≤ 15.0 | 中等置信度 | 触发 CoT 重试，或降维追问 |
| σ > 15.0 | 低置信度 | 丢弃成绩，前端仲裁介入 |
| 连续 3 次中置信度 | 累计熔断 | 前端仲裁介入 |

代码实现见 `src/graph/governance.py`：

```python
def calculate_std(scores: list[int]) -> float:
    """计算标准差，N ≤ 1 时返回 0。"""
    if len(scores) <= 1:
        return 0.0
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    return math.sqrt(variance)

def evaluate_confidence(scores: list[int]) -> ConfidenceLevel:
    """根据 σ 区间判定置信度。"""
    sigma = calculate_std(scores)
    if sigma <= 5.0:
        return ConfidenceLevel.HIGH
    elif sigma <= 15.0:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW
```

## 3. 计数器驱动的防死循环

四个计数器确保系统在最坏情况下也能安全退出：

| 计数器 | 作用域 | 递增时机 | 上限动作 |
|--------|--------|----------|----------|
| `retry_count` | 单议题 | 每次中置信度路由 | ≥ 3 → 跳过议题 |
| `consecutive_medium` | 全局 | 每次中置信度路由 | ≥ 3 → ESCALATE |
| `global_round_count` | 全局 | 每次候选人提交回答 | ≥ 30 → REPORTING |
| `invalid_input_count` | 当前轮次 | 检测到注入/无效输入 | ≥ 3 → 跳过议题 |

这些是**硬阈值**，不依赖 LLM 判断，保证了系统不会陷入无限循环或资源耗尽。

## 4. 多层护栏（Guardrails）

Harness 在 LLM 调用前后设置了多道确定性防线：

### 调用前：注入攻击检测

`questioner.py` 在 LLM 调用前检查候选人回答：

```python
_INJECTION_PATTERNS = [
    r"(?:ignore\s+(?:all\s+)?previous\s+(?:instructions|rules|prompts))",
    r"(?:disregard\s+(?:all\s+)?(?:previous|above)\s+(?:instructions|rules))",
    r"(?:you\s+are\s+now\s+(?:acting\s+as\s+)?(?:a|an)?\s*\w+)",
    r"(?:\bpretend\s+to\s+be\b|\bas\s+if\s+you\s+are\b)",
    r"(?:\breveal\s+(?:your|the)\s+(?:system|prompt|instructions))",
    # ... 共 12 种模式
]
```

匹配到注入模式时，直接返回引导消息，不调用 LLM。

### 调用后：评分数字拦截

`_strip_score_patterns` 移除 LLM 输出中可能出现的评分模式：

```python
text = re.sub(r"\d{1,3}\s*分", "", text)       # "80分"
text = re.sub(r"score\s*[:：]\s*\d{1,3}", "", text)  # "score: 80"
text = re.sub(r"得分\s*\d{1,3}", "", text)     # "得分 80"
```

### 评估层：Pydantic 参数校验

`submit_evaluation` 工具通过 `EvaluationInput` 模型强制校验：

```python
class EvaluationInput(BaseModel):
    score: int = Field(ge=1, le=100)
    topic_id: str = Field(min_length=1)
    rationale: str = Field(min_length=50)
```

校验失败时抛出 `ValidationError`，无效评分不计入 σ 计算。

**这些护栏不依赖 LLM 的"自觉"，而是用确定性代码兜底。**

## 5. 可观测性

Harness 记录完整的决策链，支持面试回放和审计：

| 数据 | 用途 |
|------|------|
| `chat_history` | 所有对话轨迹（含 topic_id 分区，防止跨议题污染） |
| `evaluation_records` | 所有评分及理据 |
| `routing_flag` 序列 | 每次路由决策 |
| 结构化 JSONL 日志 | 节点名、输入摘要（脱敏后）、输出摘要、耗时 |

每次面试都可以完整回放，验证 Harness 决策的正确性。

## 6. 优雅退出

Harness 捕获 `SIGINT`/`SIGTERM` 信号，将当前状态序列化到快照文件：

```python
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)
```

防止进程意外终止导致面试数据丢失。

## 总结

Harness Engineering 的核心公式：

> **用确定性代码包裹非确定性 LLM，用可测量的指标做决策，用硬阈值防失控。**

项目的 `src/graph/` 目录（`governance.py` + `router.py` + `builder.py`）加上 `src/state.py`，共同构成了这层控制。它们确保了即使 LLM 产生最差的输出，系统也能安全、可预测地流转。
