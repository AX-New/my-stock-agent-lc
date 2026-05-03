# My Stock Agent LC — LangChain 子系统

**创建时间**: 20260503 07:10

## 项目定位

基于 LangChain 的子系统，专做 LC **真正擅长**的部分：

- 研报 / 公告 / 新闻类文档的 RAG 检索
- 文档结构化抽取（PDF/HTML → Pydantic schema）
- 步骤固定、可画 DAG 的确定性流水线

**明确不做**：开放式 agent 决策、动态多工具路由、自驱探索类任务——那些回到 `my-stock-agent`（Claude Agent SDK）。

## 在 my-stock 体系中的位置

```
my-stock-agent              my-stock-agent-lc           my-stock-quant
（Claude Agent SDK）   →   （LangChain / 本项目）   →   （量化引擎）
- 开放 agent loop          - RAG 文档检索               - 把 LC 抽出的
- 自驱策略 / 因子探索      - 文档结构化抽取               信号、特征接入
- 调用 LC 当工具用         - 固定流水线                   生产
```

- **上游**：my-stock-agent 把"找一下最近研报里 X 行业的观点"这类活派给本项目
- **下游**：抽取出来的结构化结果（信号、特征、文本摘要）给 my-stock-agent 或 my-stock-quant 消费

## 部署

| 项 | 值 |
|----|-----|
| 路径 | `/opt/my-stock-agent-lc` |
| 端口 | 8004（保留） |
| Conda 环境 | `my-stock-agent-lc`（独立） |
| systemd 服务 | `my-stock-agent-lc.service`（保留） |

## 目录结构

```
my-stock-agent-lc/
├── CLAUDE.md           # Claude Code 项目说明（强约束）
├── README.md           # 本文件
├── PROGRESS.md         # 踩坑速查表
├── .claude/            # Claude Code 项目级配置
├── task/               # 工程任务跟踪
└── docs/
    ├── arc/            # 已实现架构
    ├── design/         # 未实现设计
    ├── specs/          # 接口 / 工具说明
    └── constraints/    # 强制约束
```

## 后续规划

- [ ] 选定向量库（Chroma / FAISS / 本机已部署的中间件）
- [ ] 选定文档源（研报 PDF / 公告 / 新闻 API）
- [ ] 第一个 RAG 流水线：文档加载 → 切分 → embedding → 检索 → 答案
- [ ] 跟 my-stock-agent 的调用契约（HTTP API or Python import）
