import httpx
import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from itertools import cycle
import uuid
import time

# --------------------------------------------------------------------------
# 加载配置
# --------------------------------------------------------------------------
load_dotenv()

QWEN_TOKENS = os.getenv("QWEN_TOKENS", "").split(',')
if not all(QWEN_TOKENS):
    raise ValueError("QWEN_TOKENS environment variable not set or empty.")

# 使用 itertools.cycle 实现 Token 轮询
token_cycler = cycle(QWEN_TOKENS)

QWEN_API_BASE_URL = "https://chat.qwen.ai"
PORT = int(os.getenv("PORT", 8220))

# 可选的鉴权头
QWEN_BX_UA = os.getenv("QWEN_BX_UA")
QWEN_BX_UMIDTOKEN = os.getenv("QWEN_BX_UMIDTOKEN")
QWEN_BX_V = os.getenv("QWEN_BX_V", "2.5.31")
QWEN_SOURCE = os.getenv("QWEN_SOURCE", "web")
QWEN_TIMEZONE = os.getenv("QWEN_TIMEZONE", "Asia/Shanghai")

# --------------------------------------------------------------------------
# Qwen API 客户端
# --------------------------------------------------------------------------

class QwenClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = self._get_base_headers()

    def _get_base_headers(self):
        """构造模拟浏览器的请求头"""
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Authorization': f'Bearer {self.token}',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json; charset=UTF-8',
            'Origin': 'https://chat.qwen.ai',
            'Pragma': 'no-cache',
            'Referer': 'https://chat.qwen.ai/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
            'source': QWEN_SOURCE,
            'timezone': QWEN_TIMEZONE,
            'x-request-id': str(uuid.uuid4()),
        }
        
        # 添加可选的鉴权头
        if QWEN_BX_UA:
            headers['bx-ua'] = QWEN_BX_UA
        if QWEN_BX_UMIDTOKEN:
            headers['bx-umidtoken'] = QWEN_BX_UMIDTOKEN
        if QWEN_BX_V:
            headers['bx-v'] = QWEN_BX_V
            
        return headers

    async def _request(self, method: str, url: str, **kwargs):
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                error_content = e.response.text
                raise HTTPException(status_code=e.response.status_code, detail=f"Error from Qwen API: {error_content}")
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Service Unavailable: {str(e)}")

    async def create_new_chat(self, model: str, title: str = "新建对话"):
        """创建一个新的对话，返回 chat_id"""
        url = f"{QWEN_API_BASE_URL}/api/v2/chats/new"
        payload = {
            "title": title,
            "models": [model],
            "chat_mode": "normal",
            "chat_type": "search",
            "timestamp": int(time.time() * 1000),
        }
        response = await self._request("POST", url, headers=self.headers, json=payload)
        data = response.json()
        if data.get("success") and data.get("data", {}).get("id"):
            return data["data"]["id"]
        else:
            raise HTTPException(status_code=500, detail=f"Failed to create new chat: {data}")

    async def stream_chat_completions(self, chat_id: str, payload: dict):
        """以流式方式请求聊天补全"""
        url = f"{QWEN_API_BASE_URL}/api/v2/chat/completions?chat_id={chat_id}"
        headers = self.headers.copy()
        headers['x-accel-buffering'] = 'no'
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_content = await response.aread()
                    yield f"data: {{\"error\": \"{error_content.decode('utf-8')}\"}}\n\n"
                else:
                    async for chunk in response.aiter_bytes():
                        yield chunk

    async def chat_completions(self, chat_id: str, payload: dict):
        """请求非流式聊天补全"""
        url = f"{QWEN_API_BASE_URL}/api/v2/chat/completions?chat_id={chat_id}"
        response = await self._request("POST", url, headers=self.headers, json=payload)
        return response.json()

# --------------------------------------------------------------------------
# FastAPI 应用
# --------------------------------------------------------------------------

app = FastAPI(
    title="Qwen Web V2 API Wrapper",
    description="一个 FastAPI 服务，用于封装通义千问 Web UI 的 V2 API，支持多 Token 轮询。",
    version="2.0.0",
)

@app.post("/v1/chat/completions")
async def api_chat_completions(request: Request):
    """
    兼容 OpenAI 格式的聊天请求端点。
    自动处理 chat_id 创建和消息发送。
    """
    token = next(token_cycler)
    qwen_client = QwenClient(token)

    try:
        openai_payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    model = openai_payload.get("model", "qwen3-coder-plus")
    messages = openai_payload.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="'messages' field is required.")

    # 从请求中获取或创建 chat_id
    # 简单起见，我们每次都创建一个新的对话。也可以通过传入 chat_id 来继续对话。
    chat_id = openai_payload.get("chat_id")
    if not chat_id:
        chat_id = await qwen_client.create_new_chat(model)

    # 构造 Qwen V2 请求体
    qwen_payload = {
        "stream": openai_payload.get("stream", False),
        "incremental_output": True,
        "chat_id": chat_id,
        "chat_mode": "normal",
        "model": model,
        "parent_id": None, # 可根据需要实现上下文
        "messages": messages,
        "timestamp": int(time.time() * 1000),
        "size": f"{len(messages)}:{len(messages)}"
    }

    is_stream = qwen_payload.get("stream", False)
    if is_stream:
        return StreamingResponse(qwen_client.stream_chat_completions(chat_id, qwen_payload), media_type="text/event-stream")
    else:
        response_data = await qwen_client.chat_completions(chat_id, qwen_payload)
        return JSONResponse(content=response_data)

@app.get("/")
async def root():
    return {"message": "Qwen Web V2 API Wrapper is running. See /docs for API documentation."}

@app.get("/v1/models")
async def get_models():
    """兼容 OpenAI 的模型列表接口"""
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen3-235b-a22b",
                "object": "model",
                "created": 1722844800,
                "owned_by": "qwen"
            },
            {
                "id": "qwen3-coder-plus",
                "object": "model",
                "created": 1722844800,
                "owned_by": "qwen"
            },
            {
                "id": "qwen3-coder-30b-a3b-instruct",
                "object": "model",
                "created": 1722844800,
                "owned_by": "qwen"
            }
        ]
    }

# --------------------------------------------------------------------------
# 启动服务
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("--- Qwen Web V2 API Wrapper ---")
    print(f"Loaded {len(QWEN_TOKENS)} tokens.")
    print(f"Access the API documentation at http://127.0.0.1:{PORT}/docs")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
