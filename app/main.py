"""
主应用文件 - 整合WebSocket和HTTP
功能：启动整合服务器，处理WebSocket和HTTP请求
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

# 导入数据库和模型
from app .database import engine, Base
from app .models import Tool, Employee, BorrowRecord
from app .websocket_server import handle_websocket_connection
from app .record_handler import init_employee
from app .http_server import app as http_app

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建主FastAPI应用
app = FastAPI(
    title="智能工具柜混合服务器",
    version="1.0.0",
    description="WebSocket实时通信 + HTTP历史查询"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载HTTP应用
app.mount("/api", http_app)  # HTTP API挂载到/api路径下


# WebSocket端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket主连接端点

    参数:
    - websocket: WebSocket连接对象
    """
    await handle_websocket_connection(websocket)  # 处理WebSocket连接


# HTTP健康检查接口
@app.get("/")
def root():
    """
    根路径，返回服务器信息

    返回: JSON格式的服务器信息
    """
    return {
        "service": "智能工具柜混合服务器",
        "version": "1.0.0",
        "protocols": {
            "websocket": "/ws",
            "http_api": "/api"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
def health_check():
    """
    健康检查接口

    返回: JSON格式的健康状态
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# 服务器启动事件
@app.on_event("startup")
async def startup_event():
    """
    服务器启动时执行
    创建数据库表和初始化数据
    """
    logger.info("服务器启动中...")

    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")

    # 初始化员工数据
    init_employee()
    logger.info("数据初始化完成")

    logger.info("服务器启动完成")


# 服务器关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """
    服务器关闭时执行
    清理资源
    """
    logger.info("服务器关闭中...")
    logger.info("服务器关闭完成")