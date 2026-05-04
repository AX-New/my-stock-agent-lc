# 切换默认 LLM Provider 到火山方舟豆包

**创建时间**: 20260504 09:50
**线程ID**: claude01
**状态**: 进行中

## 动机

- 学习项目希望默认走国内 provider，免代理、免境外账号、免计费门槛
- 火山方舟（ark.cn-beijing.volces.com）走 OpenAI 兼容协议，langchain-openai 直连即可
- 同一个 endpoint 还能挂 Doubao / Kimi / GLM / DeepSeek / MiniMax 多家模型，方便对比
- 保留 Anthropic Claude 作为备选，通过 `.env` 一键切换

## 改动点

| 文件 | 改动 |
|------|------|
| `requirements.txt` | 新增 `langchain-openai~=1.2.0`；保留 `langchain-anthropic` |
| `app/config.py` | 新增 `LLM_PROVIDER` / `VOLCENGINE_API_KEY` / `VOLCENGINE_BASE_URL`；`LLM_MODEL` 默认改 `doubao-seed-2.0-pro` |
| `app/llm.py` | `make_llm()` 按 `LLM_PROVIDER` 路由到 `ChatOpenAI` 或 `ChatAnthropic` |
| `.env.example` / `.env` | 字段重排，默认 volcengine |
| `CLAUDE.md` | 第 3 条 LangChain 约束改成"默认 volcengine 豆包" |
| `docs/arc/010-...` | 技术选型表更新 |

## 默认模型决策

- `ark-code-latest`（用户配置标记 primary，但 32K maxTokens）
- `doubao-seed-2.0-pro` ← **选这个**（128K maxTokens、通用、最稳）
- `doubao-seed-2.0-code`（code 向，128K）
- 其他（kimi/glm/deepseek/minimax）作为备选

理由：本项目是 agent 学习，需要 tool calling + RAG + 多步规划，通用模型最稳。
用户可通过 `LLM_MODEL` 环境变量自由切换。

## 风险点（需 smoke test 验证）

1. **Tool calling 支持**：豆包走 OpenAI 兼容协议，理论支持 function calling。
   - `single_agent` / `rag_agent` 依赖 tool calling
   - `multi_agent` 的 supervisor 用了 `with_structured_output`（也是 tool calling）
   - 若某模型不支持，supervisor 要降级成手动 JSON 解析
2. **Streaming**：OpenAI 协议标准 SSE，`langchain-openai` 默认透明处理，应该 OK
3. **`/api/coding/v3` 网关**：和标准 `/api/v3` 可能在某些参数上有差异，实测确认

## 验收

- [ ] `single_agent`：直接对话能流式输出
- [ ] `single_agent` + 工具：`"现在几点？"` 触发 `current_time`
- [ ] `rag_agent`：`"半导体 Q1 怎么样？"` 触发 `retrieve_documents` 并引用
- [ ] `plan_agent`：能产出 plan JSON 并分步执行
- [ ] `multi_agent`：supervisor 能成功路由（依赖 structured output）

## 不做

- Anthropic 路径的 token streaming 兼容性测试（之前已验证；这次只做 volcengine 验证）
- 更细的模型 cost / 速度对比（学习项目不必要）
