# Qwen Chat WebUI 直连 API 与鉴权分析

> 本文档基于对 https://chat.qwen.ai/ 前端 WebUI 的逆向工程及抓包结果整理，旨在为后端服务直连官方 API 提供完整参考。

## 1. 登录与鉴权

| 步骤 | 说明 |
|------|------|
| 1. 邮箱登录 | 用户通过邮箱 + 密码登录，表单地址见前端 SvelteKit 路由。 |
| 2. 获取 JWT | 登录成功后，后端返回 `Authorization: Bearer <jwt>`，前端将 JWT 保存到 `localStorage`.key:`qwen-auth-token`（键名可能随版本调整）。 |
| 3. 请求携带 | 后续所有 API 请求在 Header 中添加 `Authorization: Bearer <jwt>`。 |
| 4. Token 校验 | JWT 使用 HS256，包含 `sub`(userId)、`exp` 等字段，服务端校验有效性。 |

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

## 2. 核心 API 列表

| 场景 | 方法 & 路径 | 描述 |
|------|-------------|------|
| 新建会话 | `POST /api/v2/chats/new` | 返回 `chat_id` |
| 发送消息 | `POST /api/v2/chat/completions?chat_id={chat_id}` | 支持普通 / 流式响应 |
| 查询历史 | `GET  /api/v2/chats/{chat_id}` | 拉取历史消息 |
| Token 检查 | `POST /token/check` | 后端自带接口，快速验证 JWT 有效性 |

## 3. 请求体差异（三种模式）

### 3.1 普通模式 (normal – 默认)
```json
{
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "stream": true
}
```

### 3.2 深度思考模式 (thinking)
```json
{
  "messages": [...],
  "feature_config": {
    "thinking_enabled": true
  }
}
```
*字段说明*
- `feature_config.thinking_enabled`: 启用大模型的深度思考链式推理(Chain-of-Thought)输出。

### 3.3 搜索模式 (search)
```json
{
  "messages": [...],
  "chat_mode": "search"
}
```
*字段说明*
- `chat_mode`: 设为 `search` 时，后端会触发联网搜索能力，回答中附带引用出处。

> **小结**：三种模式仅需关注 `feature_config.thinking_enabled` 与 `chat_mode` 两个参数，其他字段保持 OpenAI Chat Completions 兼容格式。

## 4. 响应格式

### 4.1 非流式
```json
{
  "id": "cmpl-xxx",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "..."},
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60}
}
```

### 4.2 流式 (SSE)
- `Content-Type: text/event-stream`
- 数据格式：`data: {"id": ..., "choices": [{"delta": {"content": "部分"}}]}`
- 以 `data: [DONE]` 结束。

## 5. main.py 直连适配策略

1. **mode 参数**：后端新增 `mode`（normal/thinking/search），默认 normal。
2. **映射逻辑**
   * `thinking` -> 注入 `feature_config.thinking_enabled = true`
   * `search` -> 注入 `chat_mode = "search"`
3. **流式支持**：透传前端 `stream=true` 时使用 `httpx.AsyncClient().stream` 返回 SSE。
4. **异常处理**：捕获 `httpx.HTTPStatusError` & `RequestError`，包装为 FastAPI `HTTPException`。

> 详细代码见 `main.py` 中 `chat_completions` 端点实现。

## 6. 调用示例

### 6.1 普通聊天
```bash
curl -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role":"user","content":"你好"}]}' \
     http://localhost:8000/v1/chat/completions
```

### 6.2 深度思考
```bash
curl -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"mode":"thinking","messages":[{"role":"user","content":"请深度思考..."}]}' \
     http://localhost:8000/v1/chat/completions
```

### 6.3 搜索模式 + 流式
```bash
curl -N -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"mode":"search","stream":true,"messages":[{"role":"user","content":"搜索最新AI新闻"}]}' \
     http://localhost:8000/v1/chat/completions
```

## 7. 后续可拓展方向

- **多模态**：新增图像生成 `/api/v2/images/generations` 等端点适配。
- **插件体系**：观察前端是否存在 `plugin_config` 字段，决定是否支持。
- **Token 自动续期**：监控 `exp` 字段，临近过期时触发刷新或重新登录。
- **统计/埋点**：`https://aplus.qwen.ai/aes.1.1` 为阿里云流量分析埋点，不影响主链路，可忽略或阻断。

---

*文档生成日期：2025-08-05 11:57 (GMT+8)*
