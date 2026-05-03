# AI Interviewer — 智能面试官自治系统

基于 LangGraph 的多 Agent 状态机，实现从简历解析、议题规划、智能提问、多路评估到人工仲裁的完整自动化面试流程。

## 特性

- **多 Agent 协作**：统筹官（Planner）、提问官（Questioner）、评估官（Evaluator）、人工仲裁者（Supervisor）各司其职
- **σ 治理引擎**：基于 3 路并行评估的标准差（σ）分析，自动决策流转（CONTINUE / RETRY / ESCALATE）
- **防注入攻击**：prompt 级 + 代码级双层防护，覆盖 12 种常见注入模式
- **PII 脱敏**：自动识别并替换电话、身份证、地址等敏感信息
- **Web UI**：React + Vite + Tailwind，支持 SSE 实时对话流和前端仲裁页面
- **REST API + SSE**：FastAPI 后端，支持面试控制、实时事件推送、报告生成
- **CI 质量门禁**：ruff + mypy + detect-secrets + Playwright E2E

## 快速开始

### 后端

```bash
# 1. 创建虚拟环境
python3 -m venv .venv && source .venv/bin/activate

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key

# 4. 启动 Web 服务（端口 8765）
uvicorn src.api.main:app --host 0.0.0.0 --port 8765

# 或 CLI 模式（使用模拟 LLM，无需 API Key）
python -m src.main --mock
```

### 前端

```bash
cd web
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，上传简历和岗位描述即可开始面试。

## 架构

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           ▼
              ┌─────────────────────┐
              │    Planner          │  解析简历 → 生成 3-5 个议题
              └────────┬────────────┘
                       ▼
              ┌─────────────────────┐
              │   Questioner        │  基于议题和历史对话生成提问
              └────────┬────────────┘
                       ▼
              ┌─────────────────────┐
              │  Parallel Evaluator │  N=3 路独立评分
              └────────┬────────────┘
                       ▼
              ┌─────────────────────┐
              │     Router (σ)      │  标准差分析 → 决策
              └─┬───────┬────┬──────┘
         σ≤5    │       │    │ σ>15  CONTINUE/SKIP/END
        ┌───────┘       │    └─────────────┐
        ▼               ▼                   ▼
 ┌────────────┐  ┌────────────┐    ┌──────────────┐
 │ Questioner │  │ Reporting  │    │ Supervisor   │
 │ (下一议题)  │  │ (生成报告)  │    │ (前端仲裁)    │
 └────────────┘  └────────────┘    └──────┬───────┘
                                           ▼
                                    ┌─────────────┐
                                    │   Router    │
                                    └─────────────┘
```

### 治理阈值

| 标准差 σ | 定性 | 动作 |
|----------|------|------|
| σ ≤ 5.0 | 高置信度 | 记录成绩，流转至下一议题 |
| 5.0 < σ ≤ 15.0 | 中等置信度 | 触发 CoT 重试，或降维追问 |
| σ > 15.0 | 低置信度 | 丢弃成绩，前端仲裁介入 |
| 连续 3 次中置信度 | 累计熔断 | 前端仲裁介入 |

- [Harness 设计](docs/harness.md) — 如何用确定性代码包裹非确定性 LLM
- [Context Engineering 设计](docs/context-engineering.md) — 如何精确控制传递给 LLM Agent 的上下文信息

### 项目结构

```
├── src/                          # 后端（LangGraph Agent 系统）
│   ├── agents/                   # 四个 Agent 节点
│   │   ├── planner.py            # 统筹官：简历解析 + 议题规划
│   │   ├── questioner.py         # 提问官：智能提问 + 注入检测
│   │   ├── evaluator.py          # 评估官：N=3 路并行评分
│   │   └── supervisor.py         # 仲裁官：人工断点
│   ├── graph/                    # Harness 层（确定性控制）
│   │   ├── builder.py            # 图构建 + 信号处理
│   │   ├── router.py             # σ 路由决策
│   │   └── governance.py         # 标准差计算 + 置信度判定
│   ├── tools/                    # 工具
│   │   ├── resume_parser.py      # PDF/Word 简历解析
│   │   └── evaluation.py         # 评分提交 + 参数校验
│   ├── api/                      # FastAPI 服务
│   │   ├── main.py               # 应用入口 + CORS
│   │   ├── routes.py             # REST 路由
│   │   ├── sse.py                # SSE 实时推送
│   │   └── sessions.py           # 多实例隔离
│   ├── utils/                    # 工具
│   │   ├── pii.py                # PII 脱敏
│   │   ├── prompts.py            # System Prompt 模板
│   │   ├── logging.py            # 结构化日志
│   │   └── config.py             # 配置加载器
│   ├── state.py                  # InterviewState 数据模型
│   └── main.py                   # CLI 入口
├── web/                          # 前端（React SPA）
│   ├── src/
│   │   ├── pages/                # 页面：Setup / Interview / Arbitration / Report
│   │   ├── stores/               # Zustand 状态管理
│   │   ├── services/             # API 客户端 + SSE 客户端
│   │   └── types/                # TypeScript 类型（自动生成）
│   └── tests-e2e/                # Playwright E2E 测试
├── scripts/
│   └── generate_ts_types.py      # 从 Pydantic 模型生成 TypeScript 类型
├── tests/                        # 后端测试
│   ├── unit/                     # 单元测试（13 个文件）
│   └── integration/              # 集成测试（3 个文件）
├── docs/
│   └── harness.md                # Harness 工程设计文档
└── specs/                        # 规格文档
    ├── p1-product-specs.md       # 业务规格
    ├── p2-plan-specs.md          # 架构规划
    └── p3-task-specs.md          # 任务清单
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/interview/start` | 启动面试（上传简历 Base64 + JD） |
| POST | `/interview/{id}/answer` | 提交候选人回答 |
| POST | `/interview/{id}/arbitrate` | 人工仲裁操作（CONTINUE/SKIP/END） |
| GET | `/interview/{id}/status` | 查询面试状态 |
| GET | `/interview/{id}/report` | 获取面试报告 |
| GET | `/interview/{id}/stream` | SSE 实时事件流 |

## 配置

### 环境变量（`.env`）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API 密钥 | 必填 |
| `LLM_API_BASE` | LLM 服务地址 | `https://api.bianxie.ai/v1` |
| `LLM_MODEL` | LLM 模型名称 | `deepseek-chat` |

### 业务配置（`config.yaml`）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `evaluator_count` | 评估官并发数 | 3 |
| `sigma_high` | 高置信度阈值 | 5.0 |
| `sigma_medium` | 中等置信度阈值 | 15.0 |
| `max_retries_per_topic` | 单议题最大重试次数 | 3 |
| `max_global_rounds` | 全局最大对话轮次 | 30 |
| `max_consecutive_medium` | 连续中置信度熔断阈值 | 3 |
| `llm_timeout` | LLM 超时时间（秒） | 30 |

## 测试

```bash
# 后端测试（118 个）
python -m pytest tests/ -v

# 前端类型检查
cd web && npx tsc --noEmit

# 前端 lint
cd web && npm run lint

# E2E 测试（需要先启动后端服务）
cd web && npx playwright test

# 预提交检查
pre-commit run --all-files
```

## CI

项目使用 GitHub Actions 作为 CI/CD 管道，包含以下检查：

- **后端**：ruff check → ruff format → detect-secrets → mypy → pytest
- **前端**：ESLint → TypeScript 类型检查 → 构建验证 → 类型生成验证

## 技术栈

| 领域 | 选型 |
|------|------|
| 图编排 | LangGraph |
| LLM 框架 | LangChain Core + ChatOpenAI |
| 数据校验 | Pydantic v2 |
| 后端 | FastAPI + uvicorn |
| 前端 | React + Vite + TypeScript + Tailwind + Zustand + Radix UI |
| 实时通信 | Server-Sent Events (SSE) |
| 测试 | pytest + hypothesis + Playwright |
| CI | GitHub Actions + pre-commit |

## 许可证

MIT
