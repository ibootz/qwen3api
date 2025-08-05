"""
Qwen API客户端模块
负责与Qwen API进行交互，包括创建对话和聊天补全
"""
import asyncio
import httpx
import logging
import json
import time
from typing import Dict, Any, AsyncGenerator
from .config import config

logger = logging.getLogger(__name__)

class QwenClient:
    """Qwen API客户端"""
    
    def __init__(self, token_group: Dict[str, str]):
        """
        初始化Qwen客户端
        
        Args:
            token_group: 包含token的字典
        """
        self.token = token_group["token"]
        self.base_url = config.qwen_api_base_url
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Host": "chat.qwen.ai",
            "source": config.qwen_source,
            "Connection": "keep-alive",
            "Origin": "https://chat.qwen.ai",
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        logger.debug(f"创建 QwenClient 实例，token: {self.token[:20]}...")
    
    async def _request(self, method: str, url: str, max_retries: int = 3, **kwargs) -> httpx.Response:
        """
        发送HTTP请求，支持重试机制
        
        Args:
            method: 请求方法
            url: 请求URL
            max_retries: 最大重试次数
            **kwargs: 其他请求参数
            
        Returns:
            httpx.Response: 响应对象
            
        Raises:
            httpx.HTTPError: 请求失败时抛出
            Exception: 重试耗尽后抛出最后一个异常
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.request(method, url, headers=self.headers, **kwargs)
                    
                    # 检查响应状态
                    if response.status_code == 200:
                        return response
                    elif response.status_code == 429:  # 限流
                        if attempt < max_retries:
                            wait_time = (2 ** attempt) + 1  # 指数退避
                            logger.warning(f"遇到限流，等待 {wait_time}s 后重试 (尝试 {attempt + 1}/{max_retries + 1})")
                            await asyncio.sleep(wait_time)
                            continue
                    elif response.status_code >= 500:  # 服务器错误
                        if attempt < max_retries:
                            wait_time = (2 ** attempt) + 1
                            logger.warning(f"服务器错误 {response.status_code}，等待 {wait_time}s 后重试 (尝试 {attempt + 1}/{max_retries + 1})")
                            await asyncio.sleep(wait_time)
                            continue
                    
                    # 其他错误直接抛出
                    response.raise_for_status()
                    return response
                    
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"网络错误: {e}，等待 {wait_time}s 后重试 (尝试 {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"网络请求最终失败: {method} {url} - {e}")
                    raise
            except httpx.HTTPError as e:
                last_exception = e
                logger.error(f"HTTP请求失败: {method} {url} - {e}")
                raise
            except Exception as e:
                last_exception = e
                logger.error(f"未知错误: {method} {url} - {e}")
                raise
        
        # 如果所有重试都失败了
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"请求失败，已重试 {max_retries} 次: {method} {url}")
    
    async def create_new_chat(self, model: str, title: str = "新建对话") -> str:
        """
        创建新的对话
        
        Args:
            model: 使用的模型名称
            title: 对话标题
            
        Returns:
            str: 对话ID
            
        Raises:
            httpx.HTTPError: API调用失败时抛出
        """
        url = f"{self.base_url}/chats/new"
        payload = {
            "title": title,
            "models": [model],
            "chat_mode": "normal",
            "chat_type": "t2t",
            "timestamp": int(time.time() * 1000)
        }
        
        logger.info(f"创建新对话: model={model}, title={title}")
        
        try:
            response = await self._request("POST", url, json=payload)
            result = response.json()
            
            if "data" in result and "id" in result["data"]:
                chat_id = result["data"]["id"]
                logger.info(f"成功创建对话: {chat_id}")
                return chat_id
            else:
                logger.error(f"创建对话响应格式错误: {result}")
                raise ValueError("创建对话失败：响应格式错误")
                
        except Exception as e:
            logger.error(f"创建对话失败: {e}")
            raise
    
    async def stream_chat_completions(
        self, 
        chat_id: str, 
        payload: dict
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天补全
        
        Args:
            chat_id: 对话ID
            payload: 请求负载
            
        Yields:
            str: SSE格式的响应数据
        """
        url = f"{self.base_url}/chat/completions?chat_id={chat_id}"
        
        logger.info(f"开始流式聊天补全: chat_id={chat_id}")
        logger.debug(f"请求负载: {json.dumps(payload, ensure_ascii=False)}")
        logger.debug(f"请求头: {json.dumps(self.headers, ensure_ascii=False)}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST", 
                    url, 
                    headers=self.headers, 
                    json=payload
                ) as response:
                    response.raise_for_status()
                    
                    logger.info("流式响应开始")
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            logger.debug(f"收到流数据: {line}")
                            yield f"{line}\n\n"
                            
        except httpx.HTTPError as e:
            logger.error(f"流式聊天补全失败: {e}")
            raise
        except Exception as e:
            logger.error(f"流式聊天补全异常: {e}")
            raise
    
    async def chat_completions(
        self, 
        chat_id: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        非流式聊天补全
        
        Args:
            chat_id: 对话ID
            payload: 请求负载
            
        Returns:
            Dict[str, Any]: API响应数据
            
        Raises:
            httpx.HTTPError: API调用失败时抛出
        """
        url = f"{self.base_url}/chat/completions?chat_id={chat_id}"
        
        logger.info(f"开始非流式聊天补全: chat_id={chat_id}")
        logger.debug(f"请求负载: {json.dumps(payload, ensure_ascii=False)}")
        
        try:
            response = await self._request("POST", url, json=payload)
            result = response.json()
            
            logger.info("非流式聊天补全完成")
            logger.debug(f"响应数据: {json.dumps(result, ensure_ascii=False)}")
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"非流式聊天补全失败: {e}")
            raise
        except Exception as e:
            logger.error(f"非流式聊天补全异常: {e}")
            raise
    
    async def list_models(self) -> Dict[str, Any]:
        """
        获取可用模型列表
        
        Returns:
            Dict[str, Any]: 模型列表数据
            
        Raises:
            httpx.HTTPError: API调用失败时抛出
        """
        url = f"{self.base_url}/models"
        
        logger.info("获取模型列表")
        
        try:
            response = await self._request("GET", url)
            result = response.json()
            
            logger.info("成功获取模型列表")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"获取模型列表失败: {e}")
            raise
        except Exception as e:
            logger.error(f"获取模型列表异常: {e}")
            raise
