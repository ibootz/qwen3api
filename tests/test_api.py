"""
API模块测试
测试FastAPI路由和处理函数
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


class TestAPI:
    """API测试类"""
    
    @pytest.fixture
    def client(self):
        """测试客户端fixture"""
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """测试根路径端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Qwen API服务已启动"
    
    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @pytest.mark.skip(reason="需要配置真实token才能测试异步路由")
    def test_list_models(self, client):
        """测试模型列表端点 - 跳过异步路由测试"""
        pass
    
    @patch('app.api.get_next_client')
    def test_chat_completions_success(self, mock_get_client, client):
        """测试聊天完成端点成功情况"""
        from unittest.mock import AsyncMock
        
        # 模拟客户端
        mock_client = AsyncMock()
        mock_client.chat_completions = AsyncMock(return_value={
            "id": "test-id",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "测试响应"
                    },
                    "finish_reason": "stop"
                }
            ]
        })
        mock_get_client.return_value = mock_client
    
        # 发送请求
        response = client.post("/v1/chat/completions", json={
            "model": "qwen3-235b-a22b",
            "messages": [
                {"role": "user", "content": "你好"}
            ]
        })
    
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
    
    def test_chat_completions_no_client(self, client):
        """测试聊天完成端点无可用客户端情况"""
        with patch('app.api.client_pool', {}):
            response = client.post("/v1/chat/completions", json={
                "model": "qwen3-235b-a22b",
                "messages": [
                    {"role": "user", "content": "你好"}
                ]
            })
            
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
    
    def test_get_config(self, client):
        """测试配置信息端点"""
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "port" in data
        assert "qwen_api_base_url" in data
        # 确保敏感信息不被暴露
        assert "qwen_token_groups" not in data
