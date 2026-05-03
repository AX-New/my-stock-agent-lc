# My Stock Agent LC - LangChain 子系统（RAG / 文档抽取 / 固定流水线）

## 项目概况

| 项 | 说明 |
|---|---|
| 定位 | 基于 LangChain 的子系统，承接 LC 真正擅长的部分：研报/公告/新闻 RAG、文档结构化抽取、provider-portable 的固定流水线。**不做开放式 agentic 探索**。 |
| 技术栈 | Python 3.11 / LangChain / LangGraph（仅在确定要状态机时） / 向量库（待定）/ FastAPI |
| 关联项目 | `my-stock-agent`（主 agent / Claude Agent SDK 形态，开放探索）、`my-stock-quant`（生产化承接方） |

## 与 my-stock-agent 的边界

**两个 agent 项目不是替代关系，是分工**：

| 项目 | 形态 | 适合的任务 |
|------|------|------|
| **my-stock-agent** | Claude Agent SDK，开放 agent loop | 自查 DB、自提分析思路、自写代码、自跑回测、自评结果——**动态决策、路径不固定** |
| **my-stock-agent-lc** | LangChain，确定性流水线 | 研报/公告/新闻 PDF → 切分 → 向量化 → 检索；新闻 → 风格信号抽取 → 入库；**步骤固定、可画 DAG** |

**绝不在 LC 项目里做开放 agent**：LangChain 的 ReAct / 多工具动态路由场景已被验证脆弱（token 爆炸、loop 卡死、多层抽象难调试），那种活全部回到 my-stock-agent 用 Claude Agent SDK 做。

**调用方向**：
- my-stock-agent 可以把 LC 项目当成「文档检索工具」调用（HTTP 或 import）
- LC 项目不调用 my-stock-agent

## 不在范围内（明确边界）

- ❌ 开放式 agentic 决策（用 Claude Agent SDK，去 my-stock-agent）
- ❌ 直接调度回测 / 训练（用 my-stock-quant 的 pipeline）
- ❌ 写生产库（`my_stock_quant`），只能写本项目自己的文档/向量库

## 代码规范

1. **工程标准** — 这是工程项目，不是研究脚本，代码要可维护、可测试
2. **注释详细** — 所有函数、关键逻辑必须写清楚中文注释
3. **日志完善** — 日志完整详实（开始/阶段完成/结束/耗时/数据量）
4. **最小实用** — 只做需要的功能，不过度设计
5. **凭据外置** — 严禁硬编码 API Key / 密码，统一走 `.env` + `os.getenv()`（不带默认值）
6. **抽象克制** — LangChain 已经抽象很多层了，**不要在它上面再叠自己的 wrapper**；多层 LCEL pipe 出问题难调，能 flat 就 flat

## Git 工作流

**默认禁止直接在 master 上提交。** 线程ID默认 `claude01`。

```
1. git pull origin master
2. git checkout -b task-{线程ID}-{内容简写}
3. 开发 commit
4. git fetch origin && git rebase origin/master
5. git checkout master && git merge task-xxx && git push origin master
6. 删除 task 分支
```

**例外（允许直连 master 的小修小补）**：单 commit 完成、不涉及代码逻辑改动的清理类工作（删文档、修 typo、调 .gitignore 等）。逻辑改动一律走 task 分支。

### 提交格式

格式: `[TAG] - {线程ID} - {描述}`，**一个 commit 只做一件事**。

| TAG | 含义 |
|-----|------|
| `[ADD]` | 新增功能/文件 |
| `[FIX]` | BUG修复 |
| `[MOD]` | 功能调整（调参、重构、优化） |
| `[DEL]` | 删除文件/功能 |

## 文档结构

> **开始任务前必须先阅读 `task/` 目录下的对应文件**，了解当前进度和上下文。

文档命名: `010-简要描述.md`，标题下方第一行写创建时间：

```
# 文档标题
**创建时间**: 20260503 17:05
```

| 目录/文件           | 用途                                                  | 什么时候看                   |
| ------------------- | ----------------------------------------------------- | ---------------------------- |
| `task/`             | **工程任务**：建功能、修bug，完成后归档删除            | 问进展、问任务、开始新工作前 |
| `PROGRESS.md`       | 踩坑速查表（问题→原因→解法，各一句话）                 | 遇到疑似踩过的坑时           |
| `docs/constraints/` | 强制约束                                              | 涉及相关开发时必读           |
| `docs/arc/`         | 已实现的架构                                          | 需要理解现有系统时           |
| `docs/design/`      | 未实现的设计方案                                      | 明确讨论未来规划时           |
| `docs/specs/`       | 使用说明（工具、外部接口参考）                         | 需要查接口/工具用法时        |
| `README.md`         | 项目概述 + 功能列表                                   | 需要项目全貌时               |

## 部署信息

| 项 | 值 |
|----|-----|
| 路径 | `/opt/my-stock-agent-lc` |
| 端口 | 8004（保留，未启用） |
| Conda 环境 | `my-stock-agent-lc`（独立新建，与 my-stock-agent 也分开，避免 LC 依赖污染主 agent） |
| systemd 服务 | `my-stock-agent-lc.service`（保留，未启用） |

```bash
# 激活环境
conda activate my-stock-agent-lc

# 运行脚本
cd /opt/my-stock-agent-lc && conda activate my-stock-agent-lc && python xxx.py
```

## LangChain 使用约束

> **LC 是工具不是信仰，能用原生 Python 解决的不要硬塞 LCEL**。

1. **拒绝多层 LCEL pipe 嵌套** — 超过 3 层就拆成显式 Python 函数链，调试更清楚
2. **LangSmith 不上** — 观测先用普通 logging + JSON dump，需要再说
3. **provider 默认 Anthropic** — 哪怕 LC 是 provider 无关的，本项目默认 Claude；要切别的 provider 必须在 task 文档里写清动机
4. **LangGraph 仅用于真状态机** — 简单 DAG 就用普通 Python，不要无脑 LangGraph
5. **版本锁** — `requirements.txt` 锁死 langchain / langchain-anthropic / langgraph 主版本，LC 升级破坏性变更频繁，不锁死会踩

## 安全规范

**严禁在代码、文档中硬编码密码、密钥、Token。** 所有凭据通过 `.env` 配置，代码中 `os.getenv()` 读取（不带默认值）。

`.env` 必须列入 `.gitignore`，提交前 `git status` 自查。
