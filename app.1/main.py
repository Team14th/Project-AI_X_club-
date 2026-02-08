"""
主应用文件 - FastAPI + WebSocket + HTTP
功能：
1. 启动后端服务器
2. 管理数据库表
3. 提供 WebSocket 和 HTTP 接口
"""
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# 导入数据库和模型
from app.database import engine, Base
from app.models import Tool, Employee, BorrowRecord
from app.record_handler import init_employee
from app.http_server import app as http_app
from app.websocket_server import handle_websocket_connection

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Lifespan 管理启动和关闭 ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务器启动和关闭事件管理"""
    # --- startup ---
    logger.info("服务器启动中...")
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")
    # 初始化员工数据
    init_employee()
    logger.info("员工数据初始化完成")
    logger.info("服务器启动完成")
    yield
    # --- shutdown ---
    logger.info("服务器关闭中...")
    logger.info("服务器关闭完成")


# ---------------- FastAPI 应用 ----------------
app = FastAPI(
    title="智能工具柜混合服务器",
    version="1.0.0",
    description="WebSocket实时通信 + HTTP历史查询",
    lifespan=lifespan  # 使用 lifespan 替代 on_event
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 挂载 HTTP 应用
app.mount("/api", http_app)

# ---------------- WebSocket ----------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 主连接端点
    """
    await handle_websocket_connection(websocket)


# ---------------- HTTP 健康检查 ----------------
@app.get("/")
def root():
    """根路径，返回服务信息"""
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
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# ---------------- 直接运行 main.py 支持 ----------------
if __name__ == "__main__":
    import uvicorn
    # 在本机直接启动
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
