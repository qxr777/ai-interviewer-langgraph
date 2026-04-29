# 智能面试官自治系统 (ai-interviewer-langgraph) 架构规划说明书

在规范驱动开发（SDD）中，**Plan（规划）阶段**是将 Specify（定义）阶段的业务意图转化为系统架构蓝图与数据契约的关键桥梁。Plan 阶段不涉及具体的底层代码逻辑（如用哪个具体的 LLM API），而是侧重于定义状态流转、图拓扑结构、接口协议以及治理策略的量化标准。

## 1. 核心状态数据契约 (State Schema Definition)
在 LangGraph 架构中，系统通过一个全局共享的状态对象（`InterviewState`）进行通信。该字典定义了所有 Agent 节点读取和写入的数据规范。

`InterviewState` 数据结构规划：
- `candidate_info` (Dict): 候选人基础信息（需经过 PII 脱敏），包含解析后的 `skills` 列表。
- `interview_plan` (List[Dict]): 面试统筹官（Planner）生成的结构化大纲队列。包含字段：`topic_id`, `topic_name`, `status` (`pending`/`in_progress`/`completed`)。
- `chat_history` (List[Message]): 包含系统提示、AI 提问与候选人回答的完整对话轨迹。每条消息附加 `topic_id` 字段，用于按议题分区检索，防止跨议题评估污染。
- `current_topic_id` (String): 当前正在进行的面试议题标识。
- `current_topic_index` (Integer): 当前议题在 `interview_plan` 中的索引位置，用于快速定位下一议题。
- `evaluation_records` (List[Dict]): 独立评估官输出的成绩集合。
- `routing_flag` (Enum): 决定图流转方向的全局信号灯（取值：`CONTINUE`, `RETRY`, `ESCALATE`, `END`）。

## 2. 图拓扑结构与节点规划 (Graph Topology Blueprint)
系统采用多节点状态机架构，以下是各执行节点的输入输出边界规划。

### 2.1 节点定义 (Nodes)
- **Node_Planner**:
  - **触发条件**: 系统初始化，`interview_plan` 为空时。
  - **行为契约**: 读取 `candidate_info` 和内置的岗位 JD，覆盖写入 `interview_plan`。
- **Node_Questioner**:
  - **触发条件**: `routing_flag` 为 `CONTINUE` 且有未完成的议题。
  - **行为契约**: 读取 `chat_history` 与 `current_topic_id`，追加生成一条角色为 AI 的提问消息至 `chat_history`。
- **Node_Parallel_Evaluator**:
  - **触发条件**: 候选人完成作答后。
  - **行为契约**: 这是一个并行执行组（Multi-worker）。启动 $N$ 个独立的评估进程读取最后一次对话，通过工具调用强制输出结构化评分（1-100 分）。
- **Node_Human_Supervisor**:
  - **触发条件**: 发生异常熔断或 `routing_flag` 为 `ESCALATE`。
  - **行为契约**: 挂起系统流转，等待外部 API 或控制台输入干预指令。

### 2.2 路由策略 (Conditional Edges / Router)
系统的核心控制流由路由函数决定，基于对 `Node_Parallel_Evaluator` 输出的统计学分析来决定下一步走向：
- **路径 A (流转至提问官)**: 如果当前议题已获得有效成绩，更新状态并向 `Node_Questioner` 流转。
- **路径 B (降维重试)**: 如果触发治理阈值（见第 4 节），将 `routing_flag` 设为 `RETRY`，返回 `Node_Questioner` 生成难度较低的澄清性问题。
- **路径 C (人工介入)**: 如果触发熔断阈值，流转至 `Node_Human_Supervisor`。

## 3. 工具调用接口契约 (Tool Calling Interfaces)
所有 Agent 必须通过预定义的结构化工具与系统状态发生交互。

### 3.1 状态更新工具：`submit_evaluation`
- **描述**: 独立评估官提交单次考核成绩的唯一入口。
- **参数校验契约**:
  - `score` (Integer): 必须是 [1, 100] 之间的整数。
  - `topic_id` (String): 必须匹配 `current_topic_id`。
  - `rationale` (String): 字符串长度 $\ge 50$，必须包含对回答的实质性分析。

### 3.2 外部感知工具：`parse_resume_document`
- **描述**: 统筹官在初始化阶段调用的解析工具。
- **参数校验契约**:
  - `file_path` (String): 合法的本地或云端 PDF/Word 路径。
- **返回契约**: 脱敏后的结构化 JSON 数据。

## 4. 非确定性治理与方差量化标准 (Harness & Governance Metrics)
为确保 1-100 分制的评估可靠性，规划基于多路采样（设定并发数 $N=3$）的标准差 $\sigma$ 阈值控制。

- **指标计算**: 对 $N$ 个并发评估官返回的 `score` 计算标准差 $\sigma$。
- **阈值与动作映射表**:
  - **区间 1：高置信度** ($\sigma \le 5.0$)
    - 定性: 评估官意见高度统一。
    - 动作: 记录平均分为最终成绩，`routing_flag` 设为 `CONTINUE`，平滑流转。
  - **区间 2：中等置信度** ($5.0 < \sigma \le 15.0$)
    - 定性: 评估存在分歧，可能候选人表述含糊。
    - 动作: 暂缓记录成绩。触发自愈机制，系统在下一轮强制启用 CoT（思维链）提示词模板重新评估，或引导提问官追问。
  - **区间 3：低置信度 / 异常熔断** ($\sigma > 15.0$ 或连续 3 次中等置信度)
    - 定性: 大模型认知严重撕裂，或面临复杂对抗输入。
    - 动作: 丢弃该轮成绩，触发 `ESCALATE`，立即流转至人工断点（Breakpoint）。

### 4.1 Harness 状态机规格 (Harness State Machine Specification)

Harness 是包裹在非确定性 LLM Agent 外面的确定性控制层。它将系统的流转规则收敛为严格的状态机，确保任何路径都不会偏离边界。

#### 4.1.1 状态定义

| 状态 | 说明 | 持续时间 |
|------|------|----------|
| `IDLE` | 系统未启动，等待面试初始化 | 瞬时 |
| `PLANNING` | 统筹官解析简历、生成大纲 | 单次 LLM 调用 |
| `QUESTIONING` | 提问官生成问题并等待候选人作答 | 单次 LLM 调用 + 用户输入等待 |
| `EVALUATING` | 多路评估官并行打分 | N 次并行 LLM 调用 |
| `ROUTING` | Harness 执行 σ 分析、决策流转 | 纯逻辑，无 LLM |
| `ESCALATED` | 系统挂起，等待人工仲裁 | 阻塞，直到人工输入 |
| `REPORTING` | 汇总所有成绩，生成面试报告 | 纯逻辑，无 LLM |
| `COMPLETED` | 面试结束，终态 | 终态 |

#### 4.1.2 状态转换表

| 当前状态 | 触发条件 | 下一状态 | 副作用 |
|----------|----------|----------|--------|
| `IDLE` | 收到有效简历 + JD | `PLANNING` | 初始化 `InterviewState` |
| `PLANNING` | 大纲生成成功（3-5 议题） | `QUESTIONING` | 设置 `interview_plan`，选取第一个议题为 `current_topic_id` |
| `PLANNING` | 大纲生成失败（0 议题或 LLM 超时） | `ESCALATED` | 记录错误，挂起 |
| `QUESTIONING` | 候选人提交回答（非空文本） | `EVALUATING` | 记录回答至 `chat_history`，重置当前议题 `retry_count = 0` |
| `QUESTIONING` | 候选人输入为空或含注入攻击模式 | `QUESTIONING` | 拒绝输入，重新提示，`invalid_input_count += 1` |
| `QUESTIONING` | 全局对话轮次 ≥ MAX_ROUNDS (30) | `REPORTING` | 强制结束，汇总已完议题 |
| `QUESTIONING` | 当前议题重试 ≥ 3 次且无剩余待完成议题 | `REPORTING` | 所有议题耗尽，强制结束，仅汇总已完议题 |
| `EVALUATING` | 收到 N 个有效评分（全部通过校验） | `ROUTING` | 写入 `evaluation_records` |
| `EVALUATING` | 部分评估器超时（< N 个评分） | `EVALUATING` | 重试超时评估器，最多 1 次 |
| `EVALUATING` | 部分评估器返回非结构化内容（解析失败），但其余 ≥ 2 个有效 | `ROUTING` | 丢弃无效评分，仅用有效评分计算 σ（需在日志中标注） |
| `EVALUATING` | 所有评估器均超时/失败 | `ESCALATED` | 记录异常，挂起 |
| `ROUTING` | σ ≤ 5.0（高置信度） | `QUESTIONING` | 记录平均分，`current_topic` 标记为完成，选取下一议题 |
| `ROUTING` | σ > 5.0 且 ≤ 15.0，`retry_count` = 0 | `QUESTIONING` | 不记录成绩，`retry_count += 1`，启用 CoT 提示词重新评估当前回答 |
| `ROUTING` | σ > 5.0 且 ≤ 15.0，`retry_count` ≥ 1（CoT 重试仍中置信） | `QUESTIONING` | 不记录成绩，`retry_count += 1`，指示提问官生成降维追问 |
| `ROUTING` | σ > 15.0（低置信度）| `ESCALATED` | 丢弃该轮成绩，挂起 |
| `ROUTING` | 当前议题 `retry_count` ≥ 3 | `QUESTIONING` | 跳过该议题，选取下一议题 |
| `ROUTING` | 连续 3 次中置信度 | `ESCALATED` | 触发累计熔断，挂起 |
| `ROUTING` | 无更多待完成议题 | `REPORTING` | 汇总所有有效成绩 |
| `ROUTING` | 候选人主动结束面试 | `REPORTING` | 汇总已完议题的有效成绩，标注未覆盖议题 |
| `ESCALATED` | 人工输入 `CONTINUE` | `QUESTIONING` | 从断点处恢复 |
| `ESCALATED` | 人工输入 `SKIP` | `QUESTIONING` | 跳过当前议题，从下一议题恢复 |
| `ESCALATED` | 人工输入 `END` | `REPORTING` | 强制结束，汇总已完议题 |
| `REPORTING` | 报告生成完成 | `COMPLETED` | 输出结构化 JSON 面试报告 |
| `REPORTING` | `evaluation_records` 为空（无有效成绩） | `COMPLETED` | 输出空报告，标记 `status: "no_valid_evaluations"`，附议题跳过/熔断原因 |

#### 4.1.3 计数器生命周期

| 计数器 | 作用域 | 初始值 | 递增时机 | 重置时机 | 上限动作 |
|--------|--------|--------|----------|----------|----------|
| `retry_count` | 单议题 | 0 | 每次中置信度路由 | 新议题开始 | ≥ 3 → 跳过议题 |
| `consecutive_medium` | 全局 | 0 | 每次中置信度路由 | 高置信度时归零 | ≥ 3 → ESCALATED |
| `global_round_count` | 全局 | 0 | 每次候选人提交回答 | 不复位 | ≥ 30 → REPORTING |
| `invalid_input_count` | 当前轮次 | 0 | 候选人输入为空或注入 | 有效输入时归零 | ≥ 3 → 强制当前议题 SKIP |

#### 4.1.4 异常处理路径

| 异常类型 | 触发点 | 处理策略 | 日志级别 |
|----------|--------|----------|----------|
| LLM 调用超时 | 任一节点 | 重试 1 次 → 仍失败则 `ESCALATED` | ERROR |
| LLM API 限流 (429) | 任一节点 | 指数退避 2s/4s/8s → 仍失败则 `ESCALATED` | WARNING |
| Pydantic 校验失败 | `submit_evaluation` | 拒绝该评分，不计入 N 路结果 | ERROR |
| 状态机非法转换 | 路由决策 | 捕获异常 → `ESCALATED` + 完整状态快照 | CRITICAL |
| 候选人断连/退出 | `QUESTIONING` | 记录已完议题 → `REPORTING` → `COMPLETED` | INFO |

#### 4.1.5 边界场景处理

| 场景 | 检测方式 | 处理策略 |
|------|----------|----------|
| 语义偏离（答非所问） | 将候选人回答与当前议题关键词/Embedding 相似度比对，低于阈值视为偏离 | 首次偏离：提醒拉回议题；`invalid_input_count` 累计 ≥ 3 → 跳过当前议题 |
| 面试语言不一致 | 简历语言 ≠ JD 语言 | 默认以候选人简历语言为准；可在初始化时通过 `--language` 参数显式指定 |
| 候选人主动结束 | 回答含明确结束意图（如"我没有其他问题了"、"面试到此结束"） | 路由至 `REPORTING`，标注未覆盖议题 |

## 5. 项目目录结构 (Project Layout)

```
src/
  __init__.py
  state.py                # InterviewState 数据模型定义 (Pydantic)
  config.py               # 全局配置（LLM 提供商、N 值、σ 阈值、重试上限）

  agents/
    __init__.py
    planner.py            # Node_Planner：简历解析 + 面试大纲生成
    questioner.py         # Node_Questioner：基于议题和历史生成提问
    evaluator.py          # Node_Parallel_Evaluator：多路独立评分
    supervisor.py         # Node_Human_Supervisor：人工断点挂起/恢复

  tools/
    __init__.py
    resume_parser.py      # parse_resume_document 工具实现
    evaluation.py         # submit_evaluation 工具 + 参数校验

  graph/
    __init__.py
    builder.py            # LangGraph 图构建（节点注册 + 条件边）
    router.py             # 路由函数：σ 分析 → CONTINUE/RETRY/ESCALATE/END
    governance.py         # 标准差计算、置信度区间判定、熔断计数

  utils/
    __init__.py
    pii.py                # PII 脱敏工具
    prompts.py            # 各角色 System Prompt 模板

tests/
  unit/
    test_state.py         # 数据契约校验（字段类型、必填校验）
    test_planner.py       # 大纲生成逻辑（输入 mock 简历 → 验证议题数）
    test_questioner.py    # 提问生成逻辑（验证不包含评分/不泄露指令）
    test_evaluator.py     # 评分校验（分数区间、理据长度、topic_id 匹配）
    test_router.py        # 路由决策分支覆盖（σ ≤ 5 / 5-15 / > 15）
    test_governance.py    # 标准差计算、熔断计数、置信度区间
    test_pii.py           # 脱敏规则（电话/地址/身份证 → 替换）

  integration/
    test_graph_flow.py    # 完整图状态流转（正常路径 + 重试路径 + 熔断路径）
    test_tools.py         # 工具链端到端（简历解析 → 大纲 → 提问 → 评分）

  fixtures/
    mock_resume.pdf       # 模拟简历文件
    sample_state.json     # 预填充的 InterviewState 快照
```

## 6. 技术选型与 MVP 范围 (Tech Stack & MVP Scope)

### 6.1 技术栈

| 领域 | 选型 | 版本约束 |
|------|------|----------|
| 图编排 | LangGraph | >= 0.2.0 |
| LLM 编排框架 | LangChain Core | 与 LangGraph 配套版本 |
| LLM 提供商（MVP） | OpenAI API (gpt-4o) | 可替换，通过 `config.py` 切换 |
| 数据校验 | Pydantic v2 | 用于 InterviewState 和工具参数校验 |
| 测试框架 | pytest + pytest-asyncio | 异步图节点测试 |
| 持久化（MVP） | LangGraph 内置 MemorySaver | MVP 阶段内存存储，后续可切换 Postgres |
| 人工断点（MVP） | 终端交互式输入 | MVP 阶段 CLI 输入，后续切换 Web API |

### 6.2 MVP 范围

**纳入 MVP（Phase 1）**:
- 简历上传 → 解析 → 生成 3-5 个议题大纲
- 单轮问答循环：提问 → 候选人文本作答 → 3 路并行评估 → σ 路由
- 高置信度路径：平滑流转至下一议题
- 中等置信度路径：触发 CoT 重试一次
- 低置信度路径：终端人工断点（输入 CONTINUE / SKIP）
- 所有议题完成后输出结构化面试报告（JSON）
- PII 脱敏、防反客为主护栏

**不纳入 MVP（Phase 2+）**:
- 语音输入/输出（仅文本）
- Web UI / API 服务（仅 CLI 运行）
- Postgres 持久化 / Checkpoint 外部存储
- 多 LLM 提供商自动切换
- 面试报告可视化（PDF/HTML 导出）

## 7. 测试策略 (Testing Strategy)

### 7.1 测试分层

| 层级 | 范围 | 工具 | 覆盖率目标 |
|------|------|------|-----------|
| 单元测试 | 单个节点/工具/函数 | pytest + mock LLM | ≥ 80% 行覆盖 |
| 集成测试 | 图完整流转路径 | LangGraph 测试 harness | 3 条路径全覆的 |
| 属性测试 | 治理指标计算 | hypothesis (随机 σ 输入) | 边界值 100% |

### 7.2 各节点可测试标准

| 节点/模块 | 测试形式 | 完成标准 |
|-----------|----------|----------|
| `InterviewState` | 单元测试 | Pydantic 模型实例化成功；非法字段被拒绝 |
| `Node_Planner` | 单元测试（mock LLM） | 输入 mock 简历 → 输出 3-5 个议题，每个议题含 topic_id/topic_name/status=pending |
| `Node_Questioner` | 单元测试（mock LLM） | 生成一条 AI 角色消息追加到 chat_history；输出不包含评分数字 |
| `Node_Parallel_Evaluator` | 单元测试（mock LLM） | N=3 并行调用 → 返回 3 个 score ∈ [1,100]，每个 rationale 长度 ≥ 50 |
| `submit_evaluation` 工具 | 单元测试 | score 越界 / topic_id 不匹配 / rationale 过短 → 抛校验异常 |
| `parse_resume_document` 工具 | 集成测试 | 输入 fixtures/mock_resume.pdf → 返回脱敏 JSON，含 skills 列表 |
| `router` 路由函数 | 单元测试 | 输入 σ=3 → CONTINUE；σ=10 → RETRY；σ=20 → ESCALATE |
| `governance` 模块 | 属性测试 | 任意 N 个分数输入 → σ 计算正确；连续 3 次中等 → 熔断 |
| `pii` 模块 | 单元测试 | 输入含电话/地址文本 → 对应字段被替换为 `[REDACTED]` |
| 完整图流转 | 集成测试 | 从空状态启动 → 经历 3 个议题 → 最终输出面试报告 JSON |
| 熔断路径 | 集成测试 | 模拟 σ > 15 → 图挂起到 Human_Supervisor → 人工输入后恢复 |

### 7.3 Mock 策略

- 所有 LLM 调用在测试中通过 `langchain_core.language_models.FakeListChatModel` 或 pytest fixture mock 返回
- 不依赖真实 API key 运行测试套件
- 集成测试中使用确定性 prompt-response 映射，避免 LLM 随机性干扰断言

## 8. 安全架构 (Security Architecture)

### 8.1 密钥与凭证管理

| 维度 | MVP 方案 | 说明 |
|------|----------|------|
| LLM API Key | 环境变量 `OPENAI_API_KEY` | 绝不硬编码或提交至版本控制 |
| 配置文件 | `.env` + `.gitignore` | 项目根目录维护 `.env.example` 模板 |
| 凭证泄漏防护 | `git-secrets` 或 `detect-secrets` pre-commit hook | 阻止密钥误提交至 git |

### 8.2 Prompt 注入防护

| 威胁场景 | 防御策略 | 实现位置 |
|----------|----------|----------|
| 候选人试图套取系统指令 | System Prompt 中设置元指令禁止层（meta-instruction layer） | `prompts.py` 各角色模板 |
| 候选人恶意输入绕过护栏 | 输入预处理：在 LLM 调用前进行关键词/模式匹配拦截 | `questioner.py` 输入拦截层 |
| Prompt 拼接注入 | 使用 LangChain 的 `ChatPromptTemplate` 而非字符串拼接 | 所有 Agent 节点统一使用模板 |

### 8.3 数据隔离与访问控制

| 维度 | 策略 |
|------|------|
| 面试数据隔离 | 每次面试实例拥有独立 `InterviewState` 实例，不同候选人之间无数据交叉 |
| PII 脱敏时机 | `parse_resume_document` 返回前执行一次；`Node_Parallel_Evaluator` 接收数据前再校验一次 |
| 评分不可见保障 | `Node_Questioner` 输出前执行后处理：正则扫描是否包含数字评分模式（如 `\d{1,3}分`），如有则截断 |

### 8.4 防死循环与资源保护

| 保护项 | 阈值 | 动作 |
|--------|------|------|
| 单议题最大重试次数 | 3 次 | 超过后强制跳过或触发 ESCALATE |
| 全局最大对话轮次 | 30 轮（可在 `config.py` 调整） | 超过后强制进入结束阶段 |
| 单轮 LLM 调用超时 | 30 秒 | 超时后重试 1 次，仍失败则触发人工断点 |
| 并行评估器最大并发 | N=3（固定） | 不随重试次数动态增加 |

## 9. 部署架构 (Deployment Architecture)

### 9.1 运行环境

| 维度 | 要求 | 说明 |
|------|------|------|
| Python 版本 | >= 3.11, < 3.14 | 3.11 为 LangGraph 最低支持版本 |
| 包管理 | `uv` 或 `pip` + `requirements.txt` | MVP 使用 `requirements.txt`，后续可切换 `pyproject.toml` |
| 依赖隔离 | 虚拟环境（venv 或 uv venv） | 不与系统 Python 混用 |

### 9.2 配置管理

```
项目根目录/
├── .env.example          # 环境变量模板（提交至 git）
├── .env                  # 实际密钥和配置（不提交，.gitignore）
├── config.yaml           # 非敏感配置（σ 阈值、N 值、最大轮次等）
└── src/config.py         # 配置加载器：从 .env + config.yaml 合并
```

- 敏感信息（API Key）仅通过 `.env` 加载
- 业务配置（阈值、并发数）通过 `config.yaml` 管理，可不经代码修改即可调整

### 9.3 CI 与质量门禁

| 阶段 | 工具 | 触发条件 | 失败动作 |
|------|------|----------|----------|
| 代码风格 | `ruff check` | 每次 commit (pre-commit) | 阻止提交 |
| 类型检查 | `mypy src/` | 每次 push | 阻止合并 |
| 单元测试 | `pytest tests/unit/` | 每次 push | 阻止合并 |
| 集成测试 | `pytest tests/integration/` | 每次 push | 阻止合并 |
| 密钥扫描 | `detect-secrets` | 每次 commit (pre-commit) | 阻止提交 |

### 9.4 日志与可观测性

| 维度 | 方案 |
|------|------|
| 结构化日志 | Python `logging` 模块 + JSON 格式，输出到 `logs/interview_{timestamp}.jsonl` |
| 日志内容 | 每次图节点执行记录：节点名、输入摘要（脱敏后）、输出摘要、耗时、LLM token 用量 |
| 异常追踪 | 所有异常通过 `logging.exception` 记录堆栈，不静默吞没 |
| 面试回放 | 完整的 `chat_history` + `evaluation_records` + `routing_flag` 序列写入日志文件，支持人工回溯整个面试过程 |

### 9.5 运行方式

```bash
# MVP：CLI 单进程启动
python -m src.main --resume ./tests/fixtures/mock_resume.pdf --jd "Senior Python Developer"

# 未来扩展（Phase 2+）：
# uvicorn src.api:app --port 8000  # FastAPI HTTP 服务
# docker compose up               # Docker 容器化部署
```

### 9.6 Graceful Shutdown（优雅退出）

MVP 使用 MemorySaver（内存持久化），进程崩溃或 Ctrl+C 会导致状态丢失。作为过渡方案：

| 触发信号 | 处理策略 |
|----------|----------|
| `SIGINT` / `SIGTERM` | 捕获信号后，将当前 `InterviewState` 序列化到 `./state_snapshot_{timestamp}.json` |
| 状态恢复 | 启动时检测 `state_snapshot_*.json`，提示用户选择恢复或重新开始 |
| 快照时机 | 每次状态转换后（即 `routing_flag` 变更时）异步写入快照文件，不阻塞主流程 |
| 快照清理 | 面试正常进入 `COMPLETED` 后，自动删除该次面试的快照文件 |