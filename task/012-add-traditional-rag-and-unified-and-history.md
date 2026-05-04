# 加 traditional_rag / unified agent + 前端会话持久化 + UI 重做

**创建时间**: 20260504 10:30
**线程ID**: claude01
**状态**: 进行中

## 动机

1. 现有 4 类 agent 都是"分别教学一种能力"的样本，**没有日常实际可用的综合体**
2. 现有 `rag` agent 是 agentic RAG（LLM 自主决定检索），**缺一个对照样本**展示传统固定流水线 RAG 的样子
3. 前端无对话历史持久化，刷新即丢，体验差
4. UI 风格朴素、可读性一般，整体体感像调试页面

## 改动

### 后端

| 文件 | 改动 |
|------|------|
| `app/agents/traditional_rag.py` | 新增。LangGraph 2 节点：`retrieve` → `generate`，无 tool loop、无 agent 决策 |
| `app/agents/unified_agent.py`   | 新增。`create_agent` 全工具 + memory + 自主决策 prompt |
| `app/api/schemas.py`            | `AgentType` Literal 增加 `traditional_rag` / `unified` |
| `app/api/server.py`             | `_agents()` 注册新 agent；带 memory 的 agent 列表加 `unified` |

### 前端（整体重做）

- 左侧栏 + 主区双栏布局；agent 选择改为侧栏卡片列表（避免下拉框被忽视）
- 配色重做（浅色 / 深色双套，跟随系统）
- 消息气泡：用户右对齐 + 头像；assistant 左对齐 + 头像；流式时打字光标
- 事件框：每 turn 一个折叠卡片（默认折叠完成态、流式时展开），不再混在消息流中
- 欢迎/空态：显示当前 agent 的示例问题卡片，点一下填进输入框
- 输入框：textarea，Enter 发送、Shift+Enter 换行、自适应高度
- **localStorage 持久化**：threadId + agentId + 最近 200 turn 历史
- 刷新页面：UI 完整恢复；后端 memory 在服务器未重启时也连续

## 设计要点

- 不引入外部 JS / CSS 库，单文件 HTML + 原生 JS，便于学习者读
- 前端绝不用 `innerHTML`，全走 `createElement` + `textContent`（之前 hook 已提示过 XSS 风险）
- 渲染纯文本，不做 markdown 解析（要做需引 marked.js + DOMPurify，超出学习项目范围）

## 验收

- [ ] 后端 6 个 agent 全部可启动
- [ ] `/api/chat` `traditional_rag` 模式：触发 retrieve 节点 + 流式回答
- [ ] `/api/chat` `unified` 模式：能根据问题自主选 RAG / calculator
- [ ] 浏览器刷新后历史完整恢复
- [ ] 切换 agent 时不丢历史，但下一条消息会用新 agent
- [ ] 清空对话同时换新 threadId（前后端一起失忆）

## 不做

- 持久化后端 memory（SqliteSaver）—— 留作下个 task
- markdown 渲染 —— 引外部库不值得
- 多会话切换（侧栏列出历史 thread 选择）—— 学习项目不需要
