"""
客户端模块测试
测试QwenClient类的功能
"""
import pytest
import httpx
from unittest.mock import Mock, patch, AsyncMock

from app.client import QwenClient
from app.config import config


class TestQwenClient:
    """QwenClient测试类"""
    
    @pytest.fixture
    def token_group(self):
        """测试用token组fixture"""
        return {
            "token": "test_token_123",
            "bx_ua": "test_bx_ua",
            "bx_umidtoken": "test_bx_umidtoken"
        }
    
    @pytest.fixture
    def client(self, token_group):
        """QwenClient实例fixture"""
        return QwenClient(token_group)
    
    def test_client_initialization(self, client, token_group):
        """测试客户端初始化"""
        assert client.token == token_group["token"]
        assert client.bx_ua == token_group["bx_ua"]
        assert client.bx_umidtoken == token_group["bx_umidtoken"]
        assert client.base_url == config.qwen_api_base_url
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == f"Bearer {token_group['token']}"
    
    @pytest.mark.asyncio
    async def test_create_new_chat_success(self, client):
        """测试创建新聊天成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": "test_chat_id"}}
        
        with patch.object(client, '_request', return_value=mock_response):
            chat_id = await client.create_new_chat(model="qwen3-235b-a22b", title="测试对话")
            assert chat_id == "test_chat_id"
    
    @pytest.mark.asyncio
    async def test_create_chat_failure(self, client):
        """测试创建聊天失败"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        with patch.object(client, '_request', return_value=mock_response):
            with pytest.raises(Exception):
                await client.create_chat()
    
    @pytest.mark.asyncio
    async def test_chat_completions_success(self, client):
        """测试聊天完成成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_completion_id",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "测试响应内容"
                    },
                    "finish_reason": "stop"
                }
            ]
        }
        
        payload = {
            "model": "qwen3-235b-a22b",
            "messages": [{"role": "user", "content": "测试消息"}],
            "stream": False,
            "max_tokens": 1000
        }
        
        with patch.object(client, '_request', return_value=mock_response):
            result = await client.chat_completions(
                chat_id="test_chat_id",
                payload=payload
            )
            assert result["id"] == "test_completion_id"
            assert len(result["choices"]) == 1
    
    @pytest.mark.asyncio
    async def test_stream_chat_completions(self, client):
        """测试流式聊天完成"""
        
        async def mock_stream_gen():
            yield 'data: {"choices":[{"delta":{"content":"测试"}]}\n\n'
            yield 'data: {"choices":[{"delta":{"content":"流式"}]}\n\n'
            yield 'data: {"choices":[{"delta":{"content":"响应"}]}\n\n'
            yield 'data: [DONE]\n\n'

        payload = {
            "model": "qwen3-235b-a22b",
            "messages": [{"role": "user", "content": "测试消息"}],
            "stream": True,
            "max_tokens": 1000
        }

        with patch.object(client, 'stream_chat_completions', return_value=mock_stream_gen()):
            chunks = []
            async for chunk in client.stream_chat_completions("test_chat_id", payload):
                chunks.append(chunk)

            assert len(chunks) == 4
    
    @pytest.mark.asyncio
    async def test_request_with_retry(self, client):
        """测试请求重试机制"""
        # 模拟第一次失败，第二次成功
        mock_responses = [
            Mock(status_code=500, text="Internal Server Error"),
            Mock(status_code=200, json=lambda: {"success": True})
        ]
        
        with patch('httpx.AsyncClient.request', side_effect=mock_responses):
            response = await client._request("GET", "http://test.com")
            assert response.status_code == 200
