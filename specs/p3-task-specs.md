# 智能面试官自治系统 - 任务清单 (tasks.md)

> 基于 specs/p2-plan-specs.md，覆盖 Phase 1（MVP）+ Phase 2（Web UI）全部范围。
> 每个任务原子化、可测试、30-90 分钟可完成。

---

## 阶段 0：项目脚手架（Phase 1）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T01 | 创建项目目录结构（src/, tests/, logs/, config.yaml）和 `requirements.txt` | 30 分钟 | 无 |
| T02 | 配置 `config.py`：从 `.env` + `config.yaml` 加载配置（σ 阈值、N 值、最大轮次等） | 45 分钟 | T01 |
| T03 | 创建 `.env.example` 模板（OPENAI_API_KEY 占位）和 `.gitignore` | 30 分钟 | T01 |

**并行**: T02 与 T03 可在 T01 完成后并行。

---

## 阶段 1：数据契约层（Phase 1）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T04 | 实现 `InterviewState` Pydantic v2 模型（candidate_info、interview_plan、chat_history、current_topic_id、current_topic_index、evaluation_records、routing_flag Enum） | 45 分钟 | T01 |
| T05 | 为 `InterviewState` 编写单元测试（字段类型校验、非法字段拒绝、实例化成功） | 45 分钟 | T04 |

---

## 阶段 2：基础设施层（Phase 1）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T06 | 实现 `utils/pii.py`：PII 脱敏工具（识别并替换电话号码、身份证号、家庭住址为 `[REDACTED]`） | 60 分钟 | T01 |
| T07 | 编写 `utils/pii.py` 单元测试（含 PII 文本 → `[REDACTED]`，无 PII 文本不变） | 45 分钟 | T06 |
| T08 | 实现 `utils/prompts.py`：各角色 System Prompt 模板（Planner/Questioner/Evaluator/Supervisor），含元指令禁止层防 Prompt 注入 | 60 分钟 | T04 |
| T09 | 创建 `tests/fixtures/mock_resume.pdf` 和 `tests/fixtures/sample_state.json` | 45 分钟 | T04 |

**并行**: T06/T07、T08、T09 可并行。

---

## 阶段 3：工具层（Phase 1）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T10 | 实现 `tools/evaluation.py`：`submit_evaluation` 工具 + Pydantic 参数校验（score ∈ [1,100]、topic_id 匹配、rationale ≥ 50 字） | 60 分钟 | T04 |
| T11 | 实现 `tools/resume_parser.py`：`parse_resume_document` 工具（解析 PDF/Word → 结构化 JSON，含 PII 脱敏） | 90 分钟 | T04, T06 |
| T12 | 为 T10 编写单元测试（score 越界 / topic_id 不匹配 / rationale 过短 → 抛校验异常） | 45 分钟 | T10 |

**并行**: T11 可与 T10/T12 并行。

---

## 阶段 4：Agent 节点层（Phase 1）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T13 | 实现 `agents/planner.py`（Node_Planner）：读取 candidate_info + JD → 调用 LLM 生成 3-5 个议题，写入 interview_plan | 90 分钟 | T04, T08 |
| T14 | 实现 `agents/questioner.py`（Node_Questioner）：读取 chat_history + current_topic_id → 生成 AI 提问追加到 chat_history；含评分数字后处理拦截 + 输入注入检测 | 90 分钟 | T04, T08 |
| T15 | 实现 `agents/evaluator.py`（Node_Parallel_Evaluator）：N=3 并行调用 LLM 评分，通过 `submit_evaluation` 工具提交结构化结果（含超时重试、部分失败处理） | 90 分钟 | T04, T08, T10 |
| T16 | 实现 `agents/supervisor.py`（Node_Human_Supervisor）：CLI 终端挂起，等待用户输入 CONTINUE/SKIP/END | 60 分钟 | T04 |
| T17 | 为 T13/T14/T15 编写单元测试（使用 FakeListChatModel mock LLM，验证输出格式、议题数、不包含评分数字） | 90 分钟 | T13, T14, T15 |

**并行**: T13 + T14 + T15 + T16 可并行。T17 需等 T13/T14/T15 完成。

---

## 阶段 5：图与 Harness 层（Phase 1）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T18 | 实现 `graph/governance.py`：标准差 σ 计算、置信度区间判定、4 个计数器（retry_count / consecutive_medium / global_round_count / invalid_input_count）生命周期管理 | 90 分钟 | T04 |
| T19 | 实现 `graph/router.py`：路由函数（输入 σ + 计数器 → 输出 CONTINUE/RETRY/ESCALATE/END），覆盖状态转换表全部 22 条规则 | 90 分钟 | T04, T18 |
| T20 | 实现 `graph/builder.py`：LangGraph 图构建（注册 4 个节点 + 条件边 + MemorySaver 持久化 + SIGINT/SIGTERM 信号捕获与状态快照） | 90 分钟 | T04, T13, T14, T15, T16, T19 |
| T21 | 为 T18/T19 编写单元测试（σ=3→CONTINUE, σ=10→RETRY, σ=20→ESCALATE；属性测试：hypothesis 随机分数输入验证 σ 计算正确） | 90 分钟 | T18, T19 |
| T22 | 实现报告生成逻辑（`REPORTING` 状态）：汇总 evaluation_records 为结构化 JSON，含空报告处理（无有效成绩时标记 status: "no_valid_evaluations"） | 60 分钟 | T04 |

**串行**: T18 → T19 → T20。T22 可与 T18→T19→T20 并行。

---

## 阶段 6：CLI 入口与日志（Phase 1）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T23 | 实现 `src/main.py`：CLI 入口（`python -m src.main --resume <path> --jd <string> --language <lang>`），启动图执行、处理候选人终端输入、输出最终面试报告 | 60 分钟 | T04, T20 |
| T24 | 实现结构化日志：每次图节点执行记录节点名、输入摘要（脱敏后）、输出摘要、耗时、LLM token 用量，输出到 `logs/interview_{timestamp}.jsonl` | 60 分钟 | T04, T20 |

**并行**: T23 与 T24 可并行。

---

## 阶段 7：集成测试（Phase 1）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T25 | 编写 `tests/integration/test_graph_flow.py`：正常路径集成测试（从空状态启动 → 经历 3 个议题 → 输出面试报告 JSON） | 90 分钟 | T20, T21 |
| T26 | 编写 `tests/integration/test_graph_flow.py`：重试路径 + 熔断路径集成测试（模拟 σ > 15 → 挂起到 Human_Supervisor → 人工输入后恢复） | 90 分钟 | T20, T21 |
| T27 | 编写 `tests/integration/test_tools.py`：工具链端到端测试（mock_resume.pdf → 解析 → 大纲 → 提问 → 评分） | 60 分钟 | T20, T11 |

---

## 阶段 8：后端 API 服务（Phase 2）

Phase 1 为 CLI 运行，Phase 2 需要暴露 HTTP 接口供前端调用。

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T28 | 添加 FastAPI 依赖到 `requirements.txt`（fastapi、uvicorn、sse-starlette） | 30 分钟 | T01 |
| T29 | 实现 `src/api/routes.py`：REST 路由（POST /interview/start、POST /interview/{id}/answer、POST /interview/{id}/arbitrate、GET /interview/{id}/status、GET /interview/{id}/report） | 90 分钟 | T20, T28 |
| T30 | 实现 `src/api/sse.py`：SSE 流式端点（GET /interview/{id}/stream），推送提问官生成的问题逐字输出和评估进度 | 90 分钟 | T20, T28 |
| T31 | 实现多实例隔离：每个面试创建独立 `InterviewState` + UUID interview_id，存入内存字典（后续可切换 Postgres） | 60 分钟 | T04, T29 |
| T32 | 实现 `src/api/main.py`：FastAPI 应用入口（uvicorn 启动、CORS 配置、API 路由挂载、优雅关闭） | 45 分钟 | T29, T30, T31 |
| T33 | 为 T29/T30 编写集成测试（使用 httpx.AsyncClient 调用 API，验证响应格式、SSE 事件流） | 90 分钟 | T29, T30, T32 |

**并行**: T29、T30、T31 可在 T28 完成后并行。

---

## 阶段 9：前端脚手架（Phase 2）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T34 | 初始化前端项目（`web/` 目录）：`npm create vite@latest` + TypeScript + React，配置 Tailwind CSS 和 Radix UI | 45 分钟 | T01 |
| T35 | 配置 `scripts/generate_ts_types.py` CI 脚本：从后端 Pydantic 模型生成 `web/src/types/generated.ts` TypeScript 接口 | 60 分钟 | T04, T34 |
| T36 | 安装并配置 Zustand（状态管理）和 TanStack Query（数据获取），创建项目目录结构（components/ pages/ stores/ services/） | 45 分钟 | T34 |

**并行**: T35 与 T36 可在 T34 完成后并行。

---

## 阶段 10：前端页面与组件（Phase 2）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T37 | 实现 Interview 页面（`web/src/pages/Interview.tsx`）：对话消息列表、用户输入框、提交按钮、流式问题显示 | 90 分钟 | T34, T35, T36 |
| T38 | 实现 Arbitration 页面（`web/src/pages/Arbitration.tsx`）：显示当前议题、候选人最后回答、评估分歧详情、CONTINUE/SKIP/END 按钮 | 60 分钟 | T34, T35, T36 |
| T39 | 实现 Report 页面（`web/src/pages/Report.tsx`）：议题进度条、各议题平均分表格、总体评估结论 | 60 分钟 | T34, T35, T36 |
| T40 | 实现路由配置（React Router）：首页 → 输入简历和 JD → 启动面试 → 根据 `routing_flag` 跳转至 Interview/Arbitration/Report 页面 | 60 分钟 | T34, T36, T37, T38, T39 |

**并行**: T37 + T38 + T39 + T40 可并行（T40 需等页面组件基本完成）。

---

## 阶段 11：前端状态管理与 API 客户端（Phase 2）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T41 | 实现 `web/src/services/api.ts`：REST API 客户端（启动面试、提交回答、仲裁操作、获取报告） | 60 分钟 | T34, T35 |
| T42 | 实现 `web/src/services/sse.ts`：SSE 客户端（监听 /interview/{id}/stream，逐字推送消息到聊天组件） | 60 分钟 | T34 |
| T43 | 实现 `web/src/stores/interviewStore.ts`：Zustand 状态管理（interviewState、chatHistory、currentTopic、routingFlag，与后端 InterviewState 对齐） | 60 分钟 | T34, T35, T41 |
| T44 | 实现 `web/src/stores/uiStore.ts`：UI 状态管理（页面加载态、错误提示、Toast 通知） | 45 分钟 | T34 |

**并行**: T41 + T42 可并行。T43 需等 T41 完成。T44 可与其他并行。

---

## 阶段 12：前后端联调与 E2E 测试（Phase 2）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T45 | 联调：启动 FastAPI + Vite 开发服务器，验证面试启动 → 问答循环 → SSE 流式推送完整链路 | 90 分钟 | T32, T37, T41, T42, T43 |
| T46 | 联调：验证 Arbitration 页面 → 人工操作 → 恢复面试流程的完整链路 | 60 分钟 | T32, T38, T41, T43 |
| T47 | 编写 `web/tests-e2e/` 端到端测试（Playwright）：正常路径 E2E（启动 → 问答 → 报告页面） | 90 分钟 | T45 |
| T48 | 编写 `web/tests-e2e/` 端到端测试（Playwright）：熔断路径 E2E（仲裁页面出现 → 人工操作 → 恢复） | 90 分钟 | T46, T47 |

---

## 阶段 13：CI 质量门禁（全局）

| 任务 | 说明 | 时间估计 | 依赖 |
|------|------|----------|------|
| T49 | 配置 `ruff`（Python 代码风格）和 `mypy`（类型检查），编写 `pyproject.toml` 或 `ruff.toml` | 45 分钟 | T01 |
| T50 | 配置前端 lint（ESLint + Prettier）和类型检查（tsc --noEmit） | 45 分钟 | T34 |
| T51 | 配置 pre-commit hooks（ruff check + detect-secrets），编写 GitHub Actions workflow（后端：ruff + mypy + pytest；前端：eslint + tsc；E2E：Playwright） | 90 分钟 | T49, T50, T25, T26, T27, T47, T48 |

**并行**: T49 可与阶段 1-6 并行。T50 可与阶段 9-11 并行。T51 需等所有测试完成。

---

## 任务依赖图

```
Phase 1: 后端 MVP
═══════════════════════════════════════════════════════

T01 (脚手架)
├── T02 (配置) ─────────────────────────────────────────┐
├── T03 (.env)                                          │
├── T04 (State) ────┬── T05 (State 测试)                 │
│                   ├── T08 (Prompts) ──┬── T13 (Planner)│
│                   ├── T06 (PII) ──┬── T07 (PII 测试)   │
│                   │               └── T11 (Parser)     │
│                   └── T10 (Eval Tool) ──┬── T12 (测试) │
│                                        └── T15 (Evaluator)
│                                                │
T49 (CI 配置) ────────────────────────────────────┤     │
                                                  │     │
                                                  ▼     ▼
                                          T19 (Router) ←── T18 (Governance)
                                            │
                                            ▼
                                          T20 (Graph Builder) ──┬── T22 (报告)
                                            │                   ├── T23 (CLI)
                                            │                   └── T24 (日志)
                                            ▼
                                          T25 (集成-正常)
                                          T26 (集成-熔断)
                                          T27 (集成-工具链)


Phase 2: 后端 API + 前端 Web UI
═══════════════════════════════════════════════════════

T28 (FastAPI 依赖)
  ├── T29 (REST 路由) ─────────┐
  ├── T30 (SSE 端点) ──────────┤
  └── T31 (多实例隔离) ────────┤
                               ▼
                          T32 (FastAPI 入口)
                               │
    ┌──────────────────────────┼─────────────────────────┐
    │ T34 (Vite 脚手架)        │ T33 (API 测试)           │
    │   ├── T35 (类型生成)     │                          │
    │   └── T36 (Zustand)      │                          │
    │                          │                          │
    │   ├── T37 (Interview 页) │                          │
    │   ├── T38 (Arbitration)  │                          │
    │   ├── T39 (Report 页)    │                          │
    │   └── T40 (路由)         │                          │
    │                          │                          │
    │   ├── T41 (REST 客户端)  │                          │
    │   ├── T42 (SSE 客户端)   │                          │
    │   │                      │                          │
    │   ├── T43 (Zustand store)│                          │
    │   └── T44 (UI store)     │                          │
    │                          │                          │
    │   └── T45 (联调-正常) ───┼──────────────────────────┘
    │       └── T46 (联调-熔断)│
    │                          │
    └── T47 (E2E-正常)         │
        └── T48 (E2E-熔断)     │
                               │
    ┌── T50 (前端 lint) ───────┘
    │
T49 ─┤
    └── T51 (GitHub Actions) ── 全项目完成
```

## 阶段执行建议

### Phase 1（MVP 后端）

| 阶段 | 预计总时间 | 建议并行组 |
|------|-----------|-----------|
| 阶段 0：脚手架 | 2h | T02 + T03 |
| 阶段 1：数据契约 | 1.5h | 串行 |
| 阶段 2：基础设施 | 4h | T06/T07 + T08 + T09 并行 |
| 阶段 3：工具层 | 3.5h | T10/T12 + T11 并行 |
| 阶段 4：Agent 节点 | 7.5h | T13 + T14 + T15 + T16 并行，然后 T17 |
| 阶段 5：图与 Harness | 7h | T22 + T18→T19→T20 并行 |
| 阶段 6：CLI 入口 | 2h | T23 + T24 并行 |
| 阶段 7：集成测试 | 4h | 串行 |
| **Phase 1 小计** | **~31.5h** | 实际约 **2.5 个工作日** |

### Phase 2（后端 API + 前端 Web）

| 阶段 | 预计总时间 | 建议并行组 |
|------|-----------|-----------|
| 阶段 8：后端 API | 7h | T29 + T30 + T31 并行，然后 T32 + T33 |
| 阶段 9：前端脚手架 | 2.5h | T35 + T36 并行 |
| 阶段 10：前端页面 | 5.5h | T37 + T38 + T39 并行，然后 T40 |
| 阶段 11：状态管理 | 4.25h | T41 + T42 并行，然后 T43；T44 可并行 |
| 阶段 12：联调 + E2E | 6.5h | 串行 |
| 阶段 13：CI 门禁 | 3.5h | T49 + T50 可早期并行，T51 最后 |
| **Phase 2 小计** | **~29.25h** | 实际约 **2-2.5 个工作日** |

### 总计

| 阶段 | 时间 |
|------|------|
| Phase 1（MVP 后端） | ~31.5h |
| Phase 2（后端 API + 前端 Web） | ~29.25h |
| **全部** | **~61h** |
| 实际工期（考虑并行） | **约 5 个工作日** |
