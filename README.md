# Qwen3API

一个基于 FastAPI 的 Qwen3 聊天 API 代理服务，支持多 Token 轮询、Docker 部署，并提供兼容 OpenAI 的接口。

> **注意**：本项目使用 `uv` 进行依赖管理，使用 `asdf` 进行 Python 版本管理。

## 特性

- ✅ **兼容 OpenAI API 格式**：可直接替换 OpenAI 客户端的 base_url
- ✅ **多 Token 轮询**：支持配置多个 JWT Token，自动轮换使用避免限流
- ✅ **Docker 支持**：提供 Dockerfile 和 docker-compose.yml 一键部署
- ✅ **支持的模型**：qwen3-235b-a22b、qwen3-coder-plus、qwen3-coder-30b-a3b-instruct
- ✅ **流式响应**：支持 Server-Sent Events (SSE) 流式输出
- ✅ **自动会话管理**：自动创建和管理 chat_id
- ✅ **深度思考模式**：支持通过参数启用深度思考模式

## 快速开始

### 1. 环境准备

确保已安装 [asdf](https://asdf-vm.com/) 和 [uv](https://github.com/astral-sh/uv)。

```bash
# 安装 Python 插件（如果尚未安装）
asdf plugin add python

# 查看可用的 Python 版本
asdf list all python

# 安装项目所需的 Python 版本（替换 x.x.x 为具体版本号）
asdf install python x.x.x

# 设置项目 Python 版本
asdf set python x.x.x

# 验证 Python 版本
python --version
```

### 2. 安装依赖

```bash
# 创建并激活虚拟环境
uv venv -p $(asdf which python) .venv
source .venv/bin/activate

# 安装项目依赖
uv pip install -e .
```

### 2. 配置环境变量

#### 配置方式

推荐使用 YAML 配置文件，更加清晰优雅：

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

如果仍想使用环境变量配置，请参考 `.env.example` 文件。

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

# 方式2：使用模型名称后缀-thinking
curl -X POST http://localhost:8220/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "model": "qwen3-coder-plus-thinking",
    "messages": [{"role": "user", "content": "请深度思考这个问题"}]
  }'
```

### 搜索模式（使用模型名称后缀-search）+ 流式响应
```bash
curl -N -X POST http://localhost:8220/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "model": "qwen3-coder-plus-search",
    "stream": true,
    "messages": [{"role": "user", "content": "搜索最新AI新闻"}]
  }'
```

## TODO：图片or文件模式


## 配置选项

### YAML 配置文件（推荐）

| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| `qwen_token_groups` | Token组配置列表 | 必填 |
| `port` | 服务端口 | `8220` |
| `qwen_source` | 来源标识 | `web` |
| `qwen_timezone` | 时区设置 | `Asia/Shanghai` |

### 环境变量（兼容模式）

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `CONFIG_FILE` | YAML配置文件路径 | `config.yaml` |
| `QWEN_TOKEN_GROUPS` | Token组配置（格式：token） | 可选 |
| `QWEN_TOKENS` | JWT Token列表（逗号分隔，不推荐） | 可选 |
| `PORT` | 服务端口 | `8220` |
| `QWEN_API_BASE_URL` | Qwen API基础URL | `https://chat.qwen.ai` |
| `QWEN_SOURCE` | 来源标识 | `web` |
| `QWEN_TIMEZONE` | 时区设置 | `Asia/Shanghai` |

## 获取鉴权信息

1. 访问 https://chat.qwen.ai
2. 登录你的账号
3. 打开浏览器开发者工具 (F12)
4. 在 Network 面板中，找到任意 API 请求
5. 复制以下值到 `config.yaml` 文件中：
   - **token**: 从请求头的 `Authorization` 中提取（去掉 `Bearer ` 前缀）

## 开发

### 项目结构

```
qwen3api/
├── app/                 # 应用代码
│   ├── __init__.py
│   ├── api.py          # API 路由
│   ├── client.py       # Qwen 客户端
│   └── config.py       # 配置管理
├── tests/              # 测试代码
│   └── test_api.py
├── main.py             # 主程序入口
├── Dockerfile          # Docker 镜像构建文件
├── docker-compose.yml  # Docker Compose 配置
├── pyproject.toml      # 项目元数据和依赖配置
├── .python-version     # asdf Python 版本配置
└── docs/               # 文档
    └── Qwen_API_analysis.md  # API 分析文档
```

### 本地开发

确保已激活虚拟环境：

```bash
source .venv/bin/activate
```

#### 安装开发依赖
```bash
uv pip install -e ".[dev]"
```

#### 运行开发服务器（自动重载）
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8220
```

#### 代码质量检查
```bash
# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run isort .

# 静态类型检查
uv run mypy .
```

## 许可证

MIT License
