# Qwen3API

一个基于 FastAPI 的 Qwen3 聊天 API 代理服务，支持多 Token 轮询、Docker 部署，并提供兼容 OpenAI 的接口。

## 特性

- ✅ **兼容 OpenAI API 格式**：可直接替换 OpenAI 客户端的 base_url
- ✅ **多 Token 轮询**：支持配置多个 JWT Token，自动轮换使用避免限流
- ✅ **Docker 支持**：提供 Dockerfile 和 docker-compose.yml 一键部署
- ✅ **三种模式**：普通聊天、深度思考、搜索模式
- ✅ **流式响应**：支持 Server-Sent Events (SSE) 流式输出
- ✅ **自动会话管理**：自动创建和管理 chat_id

## 快速开始

### 1. 安装依赖

#### 方式一：直接运行
```bash
pip install -r requirements.txt
```

#### 方式二：使用 Poetry
```bash
poetry install
```

### 2. 配置环境变量

复制配置文件模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 JWT Token（可配置多个，用逗号分隔）：
```bash
QWEN_TOKENS=your_jwt_token_1,your_jwt_token_2,your_jwt_token_3
PORT=8220
```

### 3. 启动服务

#### 直接运行
```bash
python main.py
```

#### 使用 Docker
```bash
docker-compose up --build
```

服务启动后，访问 http://localhost:8220/docs 查看 API 文档。

## API 使用

### 获取模型列表
```bash
curl http://localhost:8220/v1/models
```

### 普通聊天
```bash
curl -X POST http://localhost:8220/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "model": "qwen3-coder-plus",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 深度思考模式
```bash
curl -X POST http://localhost:8220/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "model": "qwen3-coder-plus",
    "mode": "thinking",
    "messages": [{"role": "user", "content": "请深度思考这个问题"}]
  }'
```

### 搜索模式 + 流式响应
```bash
curl -N -X POST http://localhost:8220/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "model": "qwen3-coder-plus",
    "mode": "search",
    "stream": true,
    "messages": [{"role": "user", "content": "搜索最新AI新闻"}]
  }'
```

## 支持的模型

- `qwen3-235b-a22b`
- `qwen3-coder-plus`
- `qwen3-coder-30b-a3b-instruct`

## 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `QWEN_TOKENS` | JWT Token列表（逗号分隔） | 必填 |
| `PORT` | 服务端口 | `8220` |
| `QWEN_API_BASE_URL` | Qwen API基础URL | `https://chat.qwen.ai` |

## 获取 JWT Token

1. 访问 https://chat.qwen.ai
2. 登录你的账号
3. 打开浏览器开发者工具 (F12)
4. 在 Application/Storage 中找到 `token` 或 `qwen-auth-token`
5. 复制 Token 值到 `.env` 文件中

## 开发

### 项目结构
```
qwen3api/
├── main.py              # 主程序
├── Dockerfile          # Docker镜像构建文件
├── docker-compose.yml  # Docker Compose配置
├── .env.example        # 环境变量模板
├── pyproject.toml      # 项目依赖配置
└── docs/
    └── Qwen_API_analysis.md  # API分析文档
```

### 本地开发
```bash
# 安装开发依赖
pip install -e .

# 运行开发服务器（自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8220
```

## 许可证

MIT License
