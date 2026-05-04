# LangChain + 传统 Agent 学习系统

**创建时间**: 20260504 09:00
**线程ID**: claude01
**状态**: 进行中

## 目标

用 LangChain 一次性复刻一套完整传统 agent 形态，作为团队 LC 学习样本。包含：
tool use / memory / plan / multi-agent / RAG / SSE / Web UI。

## 技术选型

| 模块 | 选型 | 理由 |
|------|------|------|
| LLM | `claude-sonnet-4-6`（默认） | 项目约束 provider 默认 Anthropic |
| 向量库 | ChromaDB（本地持久化） | 零运维、Python 原生、最适合学习 |
| Embedding | `BAAI/bge-small-zh-v1.5` (sentence-transformers) | 中文友好、本地、~100MB |
| Web 框架 | FastAPI | 项目约束，已在 my-stock 系列统一 |
| SSE 实现 | FastAPI `StreamingResponse` + `text/event-stream` | LangChain 的 `astream_events` 直接转 SSE |
| 前端 | 单文件 HTML + 原生 JS（EventSource） | 学习项目无需 build 工具链 |
| Multi-agent 编排 | LangGraph `StateGraph` + supervisor 模式 | LC 官方推荐的多 agent 形态 |
| Plan 模式 | LangGraph 实现 plan-and-execute | LC 官方 cookbook 同款 |

## 架构

```
┌─────────────────────────────────────────────────────┐
│                  Web UI (HTML+JS)                   │
│   下拉选 agent 类型 → 输入消息 → SSE 流式渲染       │
└──────────────┬──────────────────────────────────────┘
               │ POST /chat (SSE)
┌──────────────▼──────────────────────────────────────┐
│                   FastAPI Server                    │
│  路由按 agent 类型分发：                             │
│   /chat?agent=single    → SingleAgent               │
│   /chat?agent=rag       → RagAgent                  │
│   /chat?agent=plan      → PlanExecuteAgent          │
│   /chat?agent=multi     → MultiAgentSupervisor      │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┴────────┬──────────┬──────────┐
       ▼                ▼          ▼          ▼
┌────────────┐  ┌────────────┐ ┌────────┐ ┌──────────┐
│SingleAgent │  │ RagAgent   │ │Planner │ │MultiAgent│
│tool+memory │  │+retriever  │ │ LG     │ │supervisor│
└─────┬──────┘  └─────┬──────┘ └────────┘ └──────────┘
      │               │
      ▼               ▼
┌──────────┐    ┌──────────────┐
│ Tools    │    │ Chroma RAG   │
│ - calc   │    │ + bge embed  │
│ - time   │    │ data/*.md    │
│ - search │    └──────────────┘
│ - retr   │
└──────────┘
```

## 目录骨架

```
app/
├── __init__.py
├── config.py            # 读 .env，统一配置
├── llm.py               # 创建 ChatAnthropic 实例
├── agents/
│   ├── __init__.py
│   ├── tools.py         # 计算器/当前时间/假装搜索/RAG retriever
│   ├── memory.py        # ConversationBufferMemory 包装
│   ├── single_agent.py  # tool-calling agent + memory
│   ├── rag_agent.py     # RAG 形式 agent
│   ├── planner.py       # plan-and-execute (LangGraph)
│   └── multi_agent.py   # supervisor 多 agent (LangGraph)
├── rag/
│   ├── __init__.py
│   ├── embeddings.py    # bge embeddings 加载
│   ├── vectorstore.py   # Chroma 客户端 + collection
│   └── ingest.py        # 加载 data/*.md → 切分 → 入库
├── api/
│   ├── __init__.py
│   ├── server.py        # FastAPI app
│   ├── sse.py           # SSE 工具：把 LC 事件转 SSE 行
│   └── schemas.py       # 请求/响应 pydantic
└── web/
    └── index.html       # 单页前端

data/                    # 样例文档（市场综述、行业研报片段，纯学习材料）
chroma_db/               # 向量库持久化目录
.env.example
.env                     # gitignored
requirements.txt
```

## 关键决策

1. **每种 agent 形态一个独立 endpoint**：清晰分隔展示，前端下拉切换。
2. **不做 session 持久化**：内存里存 memory，重启就丢。学习用够了。
3. **SSE 事件分类**：`token`（LLM 文本片段）/`tool`（工具调用通知）/`step`（plan 步骤切换）/`done`（结束），前端按类型渲染。
4. **Embedding 本地化**：sentence-transformers + bge，不依赖外部 embedding API，避免代理/账号问题。
5. **样例文档**：写 5-10 篇模拟"行业研报摘要 / 公司公告片段"的中文 markdown，体量小够检索演示。

## 待办

- [x] 改 CLAUDE.md / README 重新定位
- [ ] 切 task 分支 `task-claude01-langchain-agent-system`
- [ ] requirements.txt + .env.example
- [ ] 装依赖
- [ ] 写样例文档
- [ ] RAG 层：embeddings + vectorstore + ingest
- [ ] tools.py
- [ ] single_agent / rag_agent / planner / multi_agent
- [ ] FastAPI + SSE
- [ ] Web UI
- [ ] 端到端 smoke test
- [ ] 写 docs/arc/010-架构与执行流.md（实现完才写，写实际形态）
- [ ] 合 master + 推 origin

## 不做的事

- LangSmith / 监控
- 用户/会话/鉴权
- 文档持久化（只读 data/ 目录的 md）
- 多模态、音频、图像
- 生产级容错（学习项目，挂了直接看 traceback）
