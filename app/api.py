"""
API路由模块
定义所有FastAPI路由和处理函数
"""
import uuid
import logging
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from itertools import cycle

from .config import config
from .client import QwenClient

logger = logging.getLogger(__name__)

# 创建API路由
router = APIRouter()

# 全局token组轮询器
token_cycle = None

# 客户端池
client_pool = {}

def initialize_clients():
    """初始化客户端池"""
    global token_cycle, client_pool
    
    token_groups = config.get_token_groups()
    if not token_groups:
        logger.warning("未配置token组，客户端池为空")
        return
    
    token_cycle = cycle(token_groups)
    client_pool = {}
    
    # 为每个token组创建客户端
    for i, token_group in enumerate(token_groups):
        client_key = f"client_{i}"
        client_pool[client_key] = QwenClient(token_group)
        logger.debug(f"创建客户端 {client_key}: {token_group['token'][:20]}...")
    
    logger.info(f"初始化完成，共创建 {len(client_pool)} 个客户端")

async def get_next_client() -> QwenClient:
    """获取下一个可用的客户端（轮询+故障转移）"""
    if not client_pool:
        raise HTTPException(
            status_code=503,
            detail="服务不可用：未配置有效的token组"
        )
    
    if token_cycle is None:
        raise HTTPException(
            status_code=503,
            detail="服务不可用：客户端池未初始化"
        )
    
    # 尝试所有客户端，直到找到可用的
    max_attempts = len(client_pool)
    for attempt in range(max_attempts):
        # 获取下一个token组
        token_group = next(token_cycle)
        
        # 找到对应的客户端
        target_client = None
        for client in client_pool.values():
            if client.token == token_group['token']:
                target_client = client
                break
        
        # 如果没找到，创建新客户端
        if target_client is None:
            target_client = QwenClient(token_group)
            client_key = f"client_{len(client_pool)}"
            client_pool[client_key] = target_client
            logger.info(f"创建新客户端: {client_key}")
        
        # 简单健康检查（可以扩展为实际的健康检查API调用）
        try:
            # 这里可以添加实际的健康检查逻辑
            # 目前只是返回客户端，假设它是健康的
            logger.debug(f"选择客户端: token={target_client.token[:20]}...")
            return target_client
        except Exception as e:
            logger.warning(f"客户端健康检查失败: {e}，尝试下一个客户端")
            continue
    
    # 如果所有客户端都不可用
    raise HTTPException(
        status_code=503,
        detail="服务不可用：所有客户端都不可用"
    )

@router.get("/")
async def root():
    """根路径"""
    return {"message": "Qwen API服务已启动", "version": "1.0.0"}

@router.get("/v1/models")
async def list_models():
    """获取可用模型列表"""
    request_id = str(uuid.uuid4())
    logger.info(f"[请求ID: {request_id}] 获取模型列表")
    
    try:
        client = get_next_client()
        models_data = await client.list_models()
        
        # 转换格式以兼容OpenAI API
        if "data" in models_data:
            models = []
            for model in models_data["data"]:
                models.append({
                    "id": model.get("id", ""),
                    "object": "model",
                    "created": 1677610602,  # 固定时间戳
                    "owned_by": "qwen",
                    "permission": []
                })
            
            response_data = {
                "object": "list",
                "data": models
            }
            
            logger.info(f"[请求ID: {request_id}] 成功获取 {len(models)} 个模型")
            return JSONResponse(content=response_data)
        else:
            logger.warning(f"[请求ID: {request_id}] 模型数据格式异常")
            return JSONResponse(content=models_data)
            
    except Exception as e:
        logger.error(f"[请求ID: {request_id}] 获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    处理聊天完成请求
    兼容OpenAI API格式
    """
    request_id = str(uuid.uuid4())
    logger.info(f"[请求ID: {request_id}] 收到聊天补全请求")
    
    try:
        # 解析请求数据
        body = await request.json()
        logger.debug(f"[请求ID: {request_id}] 请求数据: {json.dumps(body, ensure_ascii=False)}")
        
        # 提取必要参数
        model = body.get("model")
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        max_tokens = body.get("max_tokens", 4096)
        temperature = body.get("temperature", 0)
        
        if not model:
            raise HTTPException(status_code=400, detail="缺少model参数")
        
        if not messages:
            raise HTTPException(status_code=400, detail="缺少messages参数")
        
        # 获取客户端
        client = await get_next_client()
        
        # 创建新对话
        logger.info(f"[请求ID: {request_id}] 创建新对话: model={model}")
        chat_id = await client.create_new_chat(model)
        
        # 构建Qwen Chat格式的请求负载
        import time
        
        # 生成唯一ID
        current_timestamp = int(time.time())
        
        # 转换messages格式为Qwen Chat格式
        qwen_messages = []
        for msg in messages:
            qwen_message = {
                "fid": str(uuid.uuid4()),
                "parentId": None,
                "childrenIds": [str(uuid.uuid4())],
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
                "user_action": "chat",
                "files": [],
                "timestamp": current_timestamp,
                "models": [model],
                "chat_type": "t2t",
                "feature_config": {
                    "thinking_enabled": False,
                    "output_schema": "phase"
                },
                "extra": {
                    "meta": {
                        "subChatType": "t2t"
                    }
                },
                "sub_chat_type": "t2t",
                "parent_id": None
            }
            qwen_messages.append(qwen_message)
        
        payload = {
            "stream": stream,
            "incremental_output": True,
            "chat_id": chat_id,
            "chat_mode": "normal",
            "model": model,
            "parent_id": None,
            "messages": qwen_messages,
            "timestamp": current_timestamp
        }
        
        # 处理流式或非流式响应
        if stream:
            logger.info(f"[请求ID: {request_id}] 开始流式响应")
            
            async def generate_stream():
                try:
                    async for chunk in client.stream_chat_completions(chat_id, payload):
                        yield chunk
                except Exception as e:
                    logger.error(f"[请求ID: {request_id}] 流式响应失败: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                finally:
                    yield "data: [DONE]\n\n"
            
            # 生成标准的OpenAI响应头
            response_headers = {
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream; charset=utf-8",
                "X-Request-Id": request_id,
                "X-Actual-Status-Code": "200"
            }
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers=response_headers
            )
        else:
            logger.info(f"[请求ID: {request_id}] 开始非流式响应")
            
            try:
                response_data = await client.chat_completions(chat_id, payload)
                logger.info(f"[请求ID: {request_id}] 非流式响应完成")
                
                # 添加标准的OpenAI响应头
                response_headers = {
                    "X-Request-Id": request_id,
                    "X-Actual-Status-Code": "200"
                }
                
                return JSONResponse(content=response_data, headers=response_headers)
                
            except Exception as e:
                logger.error(f"[请求ID: {request_id}] 非流式响应失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    except json.JSONDecodeError:
        logger.error(f"[请求ID: {request_id}] 请求JSON格式错误")
        raise HTTPException(status_code=400, detail="请求数据格式错误")
    except HTTPException:
        raise  # 重新抛出已定义的HTTP异常
    except Exception as e:
        logger.error(f"[请求ID: {request_id}] 处理请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": str(uuid.uuid4()),
        "clients": len(client_pool),
        "tokens": len(config.get_token_groups())
    }

@router.get("/config")
async def get_config():
    """获取当前配置信息（不包含敏感信息）"""
    return {
        "qwen_api_base_url": config.qwen_api_base_url,
        "port": config.port,
        "qwen_bx_v": config.qwen_bx_v,
        "qwen_source": config.qwen_source,
        "qwen_timezone": config.qwen_timezone,
        "token_groups_count": len(config.get_token_groups()),
        "clients_count": len(client_pool)
    }
