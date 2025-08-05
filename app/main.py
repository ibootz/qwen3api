"""
FastAPI主启动文件
负责初始化应用和启动服务
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .api import router, initialize_clients

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.log_file, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    在应用启动和关闭时执行相应的操作
    """
    # 启动时
    logger.info("正在启动 Qwen API 服务...")
    
    # 加载配置
    try:
        config.load_config()
        logger.info("配置加载完成")
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        raise
    
    # 初始化客户端
    try:
        initialize_clients()
        logger.info("客户端初始化完成")
    except Exception as e:
        logger.error(f"客户端初始化失败: {e}")
        raise
    
    logger.info(f"服务启动完成，监听端口: {config.port}")
    
    yield
    
    # 关闭时
    logger.info("正在关闭 Qwen API 服务...")

# 创建FastAPI应用
app = FastAPI(
    title="Qwen API Proxy",
    description="Qwen AI API的代理服务，提供OpenAI兼容的API接口",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.port,
        reload=False,
        log_level=config.log_level.lower()
    )
