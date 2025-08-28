#!/usr/bin/env python3
"""
Qwen API服务启动脚本
"""
import os
import sys

import uvicorn

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置
from app.config import config

if __name__ == "__main__":
    # 加载配置
    config.load_config()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.port,
        reload=True,  # 开发模式下启用热重载
        log_level="info"
    )
