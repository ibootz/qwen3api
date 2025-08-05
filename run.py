#!/usr/bin/env python3
"""
Qwen API服务启动脚本
"""
import uvicorn
import sys
import os

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8220,
        reload=True,  # 开发模式下启用热重载
        log_level="info"
    )
