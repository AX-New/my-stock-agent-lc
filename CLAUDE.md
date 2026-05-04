# My Stock Agent LC - LangChain + 传统 Agent 学习项目

## 项目概况

| 项 | 说明 |
|---|---|
| 定位 | **学习/试验项目**：用 LangChain 完整复刻一套传统 agent 形态（tool use / memory / plan / multi-agent / RAG），配 SSE 流式输出 + Web UI，作为团队 LC 选型与教学参考。 |
| 技术栈 | Python 3.11 / LangChain / LangGraph / ChromaDB / FastAPI / 原生 HTML+JS |
| 关联项目 | `my-stock-agent`（主 agent / Claude Agent SDK 形态）、`my-stock-quant`（生产化承接方） |

## 学习目标

1. **Tool Use** — LangChain tool-calling agent，挂多个工具
2. **Memory** — 会话记忆（buffer / summary）
3. **Plan** — plan-and-execute：先规划再执行
4. **Multi-Agent** — supervisor 模式，多个专精 agent 协作
5. **RAG** — ChromaDB 向量库 + retriever tool
6. **SSE** — FastAPI 流式输出 token
7. **Web UI** — 简单聊天界面，EventSource 接 SSE

## 不在范围内

- ❌ 直接写生产库（`my_stock` / `my_stock_quant`），只能用本项目自己的文档/向量库
- ❌ 直接调度回测 / 训练（那是 `my-stock-quant` 的活）

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
4. **LangGraph 用于多 agent 编排和状态机** — 简单单 agent / 单线流水线就用普通 Python，不要无脑套 LangGraph
5. **版本锁** — `requirements.txt` 锁死 langchain / langchain-anthropic / langgraph 主版本，LC 升级破坏性变更频繁，不锁死会踩

## 安全规范

**严禁在代码、文档中硬编码密码、密钥、Token。** 所有凭据通过 `.env` 配置，代码中 `os.getenv()` 读取（不带默认值）。

`.env` 必须列入 `.gitignore`，提交前 `git status` 自查。
