"""
Qwen API Proxy Application

提供Qwen AI API的代理服务，支持OpenAI兼容的API接口
"""

__version__ = "1.0.0"
__author__ = "Qwen API Team"

from .config import config
from .client import QwenClient

__all__ = ["config", "QwenClient"]
