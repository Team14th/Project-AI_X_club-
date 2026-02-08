"""
主程序入口
版本: 2.0
"""
from fastapi import FastAPI, WebSocket
from database import init_database
from websocket_server import websocket_endpoint
import uvicorn

# 创建 FastAPI 应用
app = FastAPI(title="工具借还系统后端", version="2.0")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("    工具借还可视化系统 - 后端服务")
    print("    版本: 2.0")
    init_database()
    print("✓ 后端服务已启动")
    print("✓ WebSocket 端点: ws://localhost:8000/ws")


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket 路由"""
    await websocket_endpoint(websocket)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "工具借还系统后端服务",
        "version": "2.0",
        "websocket": "ws://localhost:8000/ws"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
