# Qwen3API 项目概览

## 项目概述

Qwen3API 是一个基于 FastAPI 的 Qwen3 聊天 API 代理服务。它提供了一个与 OpenAI API 兼容的接口，允许用户通过标准的 OpenAI 客户端库与 Qwen3 模型进行交互。该项目支持多 Token 轮询、Docker 部署，并具有自动会话管理功能。

### 主要特性

- **OpenAI API 兼容**：可直接替换 OpenAI 客户端的 base_url
- **多 Token 轮询**：支持配置多个 JWT Token，自动轮换使用避免限流
- **Docker 支持**：提供 Dockerfile 和 docker-compose.yml 一键部署
- **流式响应**：支持 Server-Sent Events (SSE) 流式输出
- **自动会话管理**：自动创建和管理 chat_id
- **深度思考模式**：支持通过参数启用深度思考模式

## 技术栈

- **Python 3.12+**
- **FastAPI**：用于构建 API 的现代、快速（高性能）Python web 框架
- **Uvicorn**：用于运行 FastAPI 应用的 ASGI 服务器
- **HTTPX**：用于发送 HTTP 请求的异步 HTTP 客户端
- **PyYAML**：用于解析 YAML 配置文件

## 项目架构

```
qwen3api/
├── app/                 # 应用代码
│   ├── __init__.py
│   ├── api.py          # API 路由
│   ├── client.py       # Qwen 客户端
│   ├── config.py       # 配置管理
│   ├── main.py         # FastAPI 应用入口
│   └── validators.py   # 数据验证器
├── tests/              # 测试代码
│   └── test_api.py
├── main.py             # 主程序入口（旧版，已废弃）
├── Dockerfile          # Docker 镜像构建文件
├── docker-compose.yml  # Docker Compose 配置
├── pyproject.toml      # 项目元数据和依赖配置
├── requirements.txt    # 依赖列表（由 pyproject.toml 生成）
├── .python-version     # asdf Python 版本配置
├── config.example.yaml # 配置文件模板
└── docs/               # 文档
    └── Qwen_API_analysis.md  # API 分析文档
```

## 构建和运行

### 环境准备

项目使用 `asdf` 进行 Python 版本管理，使用 `uv` 进行依赖管理。

```bash
# 安装 asdf 和 uv（如果尚未安装）
# asdf: https://asdf-vm.com/
# uv: https://github.com/astral-sh/uv

# 安装 Python 插件（如果尚未安装）
asdf plugin add python

# 安装项目所需的 Python 版本
asdf install python 3.12.0  # 或其他 >=3.12 的版本

# 设置项目 Python 版本
asdf local python 3.12.0

# 验证 Python 版本
python --version
```

### 安装依赖

```bash
# 创建并激活虚拟环境
uv venv -p $(asdf which python) .venv
source .venv/bin/activate

# 安装项目依赖
uv pip install -e .
```

### 配置

推荐使用 YAML 配置文件：

1. 复制配置文件模板：
   ```bash
   cp config.example.yaml config.yaml
   ```

2. 编辑 `config.yaml` 文件，填入你的完整鉴权信息：
   ```yaml
   qwen_token_groups:
     - token: "your_jwt_token_1"
     - token: "your_jwt_token_2"
   
   port: 8220
   ```

### 启动服务

#### 直接运行

```bash
python run.py
```

或者使用 uvicorn 直接运行：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8220
```

#### 使用 Docker

```bash
docker-compose up --build
```

服务启动后，访问 http://localhost:8220/docs 查看 API 文档。

## 开发

### 安装开发依赖

```bash
uv pip install -e ".[dev]"
```

### 运行开发服务器（自动重载）

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8220
```

### 代码质量检查

```bash
# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run isort .

# 静态类型检查
uv run mypy .
```

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
# 方式1：使用 thinking_mode 参数（推荐）
curl -X POST http://localhost:8220/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "model": "qwen3-coder-plus",
    "thinking_mode": {
      "enabled": true
    },
    "messages": [{"role": "user", "content": "请深度思考这个问题"}]
  }'

# 方式2：使用模型名称
curl -X POST http://localhost:8220/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "model": "qwen3-deep-thinking",
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

## 获取鉴权信息

1. 访问 https://chat.qwen.ai
2. 登录你的账号
3. 打开浏览器开发者工具 (F12)
4. 在 Network 面板中，找到任意 API 请求
5. 复制以下值到 `config.yaml` 文件中：
   - **token**: 从请求头的 `Authorization` 中提取（去掉 `Bearer ` 前缀）