# My Stock Agent LC — LangChain + 传统 Agent 学习项目

**创建时间**: 20260503 07:10
**更新时间**: 20260504

## 项目定位

基于 **LangChain** 完整复刻一套传统 agent 形态，作为团队学习与选型参考：

- **Tool Use**：LangChain tool-calling agent + 多个自定义工具
- **Memory**：会话记忆（buffer / summary）
- **Plan**：plan-and-execute（先规划，再分步执行）
- **Multi-Agent**：supervisor 模式（researcher + analyst + writer 协作）
- **RAG**：ChromaDB 向量库 + retriever tool
- **SSE**：FastAPI StreamingResponse 流式输出 token
- **Web UI**：单页 HTML + EventSource，聊天形态

> 这是**学习项目**，重点是把 LangChain 各个核心模块串通走一遍；不是生产 agent。生产形态见 `my-stock-agent`（Claude Agent SDK）。

## 在 my-stock 体系中的位置

```
my-stock-agent              my-stock-agent-lc           my-stock-quant
（Claude Agent SDK）         （LangChain / 本项目）       （量化引擎）
- 生产 agent loop           - LC 各模块学习/试验          - 回测/训练生产化
- 自驱策略 / 因子探索        - RAG / multi-agent demo
```

## 快速启动

```bash
# 1. 激活环境
conda activate my-stock-agent-lc

# 2. 装依赖
cd /opt/my-stock-agent-lc
pip install -r requirements.txt

# 3. 配置密钥
cp .env.example .env
# 编辑 .env，填 ANTHROPIC_API_KEY

# 4. 灌一批样例文档进向量库
python -m app.rag.ingest

# 5. 启动服务
python -m app.api.server
# 浏览器打开 http://localhost:8004
```

## 目录结构

```
my-stock-agent-lc/
├── app/
│   ├── agents/         # 各类 agent（tool use / memory / plan / multi-agent / RAG）
│   ├── rag/            # 向量库 + 文档摄入
│   ├── api/            # FastAPI + SSE
│   └── web/            # 静态 HTML
├── data/               # 样例文档
├── chroma_db/          # 向量库持久化（gitignored）
├── task/               # 工程任务跟踪
├── docs/               # 架构 / 设计 / 约束 / 接口文档
└── requirements.txt
```

## 部署

| 项 | 值 |
|----|-----|
| 路径 | `/opt/my-stock-agent-lc` |
| 端口 | 8004 |
| Conda 环境 | `my-stock-agent-lc`（独立） |
| systemd 服务 | `my-stock-agent-lc.service`（保留，未启用） |

## 学习路线（推荐看代码顺序）

1. `app/agents/tools.py` — 自定义工具最小例
2. `app/agents/single_agent.py` — tool-calling agent + memory
3. `app/rag/vectorstore.py` + `app/rag/ingest.py` — 向量库基础
4. `app/agents/rag_agent.py` — RAG 怎么挂成 tool
5. `app/agents/planner.py` — plan-and-execute 模式
6. `app/agents/multi_agent.py` — LangGraph supervisor 多 agent
7. `app/api/server.py` — SSE 怎么把 token 流出去
8. `app/web/index.html` — 前端 EventSource 怎么收
