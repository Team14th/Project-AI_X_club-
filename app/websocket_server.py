"""
WebSocket实时服务器模块
功能：1. WebSocket连接管理 2. 工具实时操作 3. 传感器数据接收
"""
import json
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session # noqa :401
from typing import List
# 导入数据库和模型
from app.database import SessionLocal
from app.models import Tool
from app.record_handler import create_borrow_record, create_return_record  # 导入B同学的函数

# 设置日志记录器
logger = logging.getLogger(__name__)


# 存储活跃的WebSocket连接
class ConnectionManager:
    """管理WebSocket连接"""

    def __init__(self):
        # 存储所有活跃连接
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        接受新的WebSocket连接

        参数:
        - websocket: WebSocket连接对象
        """
        await websocket.accept()  # 接受客户端连接
        self.active_connections.append(websocket)  # 添加到活跃连接列表
        logger.info(f"新的WebSocket连接，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        断开WebSocket连接

        参数:
        - websocket: 要断开的连接对象
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)  # 从活跃连接移除
            logger.info(f"WebSocket连接断开，剩余连接数: {len(self.active_connections)}")

    @staticmethod
    async def send_personal_message(message: dict, websocket: WebSocket):
        """
        向特定客户端发送消息

        参数:
        - message: 要发送的消息字典
        - websocket: 目标WebSocket连接
        """
        try:
            await websocket.send_text(json.dumps(message))  # 发送JSON格式消息
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    async def broadcast(self, message: dict):
        """
        向所有连接的客户端广播消息

        参数:
        - message: 要广播的消息字典
        """
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"广播消息失败: {e}")


# 创建全局连接管理器实例
manager = ConnectionManager()


# WebSocket消息处理
async def handle_websocket_connection(websocket: WebSocket):
    """
    处理单个WebSocket连接

    参数:
    - websocket: WebSocket连接对象
    """
    await manager.connect(websocket)  # 连接客户端

    try:
        # 持续接收消息
        while True:
            data = await websocket.receive_text()  # 接收文本消息

            try:
                message = json.loads(data)  # 解析JSON消息
                logger.info(f"收到WebSocket消息: {message}")

                # 处理消息
                await process_websocket_message(websocket, message)

            except json.JSONDecodeError as e:
                # JSON解析错误
                error_msg = {
                    "type": "error",
                    "message": f"消息格式错误: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(error_msg, websocket)

    except WebSocketDisconnect:
        # 客户端断开连接
        logger.info("WebSocket连接断开")
        manager.disconnect(websocket)

    except Exception as e:
        # 其他错误
        logger.error(f"WebSocket处理错误: {e}")
        manager.disconnect(websocket)


async def process_websocket_message(websocket: WebSocket, message: dict):
    """
    处理WebSocket消息

    参数:
    - websocket: WebSocket连接对象
    - message: 消息字典
    """
    action = message.get("action", "unknown")  # 获取操作类型

    if action == "get_tool_status":
        # 获取工具当前状态
        await get_tool_status(websocket)

    elif action == "borrow_tool":
        # 借出工具
        await borrow_tool(websocket, message)

    elif action == "return_tool":
        # 归还工具
        await return_tool(websocket, message)

    elif action == "sensor_update":
        # 传感器数据更新
        await sensor_update(websocket, message)

    elif action == "ping":
        # 心跳检测
        response = {
            "type": "system",
            "action": "pong",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(response, websocket)

    else:
        # 未知操作
        error_msg = {
            "type": "error",
            "action": action,
            "message": f"未知的操作: {action}",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(error_msg, websocket)


async def get_tool_status(websocket: WebSocket):
    """
    获取工具当前状态

    参数:
    - websocket: WebSocket连接对象
    """
    db = SessionLocal()  # 创建数据库会话
    try:
        tool = db.query(Tool).filter(Tool.id == 1).first()  # 查询工具

        if not tool:
            response = {
                "type": "tool",
                "action": "get_status",
                "success": False,
                "message": "工具不存在",
                "timestamp": datetime.now().isoformat()
            }
        else:
            response = {
                "type": "tool",
                "action": "get_status",
                "success": True,
                "data": {
                    "id": tool.id,
                    "name": tool.name,
                    "total_quantity": tool.total_quantity,
                    "current_quantity": tool.current_quantity,
                    "threshold": tool.threshold,
                    "status": tool.status,
                    "last_updated": tool.last_updated.isoformat() if tool.last_updated else None
                },
                "timestamp": datetime.now().isoformat()
            }

        await manager.send_personal_message(response, websocket)  # 发送响应

    except Exception as e:
        logger.error(f"获取工具状态时出错: {e}")
        error_response = {
            "type": "error",
            "action": "get_status",
            "message": f"服务器错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(error_response, websocket)
    finally:
        db.close()  # 关闭数据库会话


async def borrow_tool(websocket: WebSocket, message: dict):
    """
    借出工具

    参数:
    - websocket: WebSocket连接对象
    - message: 消息字典
    """
    db = SessionLocal()  # 创建数据库会话
    try:
        quantity = message.get("quantity", 1)  # 获取借出数量

        if quantity <= 0:  # 验证数量
            response = {
                "type": "tool",
                "action": "borrow_tool",
                "success": False,
                "message": "借出数量必须大于0",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(response, websocket)
            return

        tool = db.query(Tool).filter(Tool.id == 1).first()  # 查询工具

        if not tool:  # 工具不存在
            response = {
                "type": "tool",
                "action": "borrow_tool",
                "success": False,
                "message": "工具不存在",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(response, websocket)
            return

        if tool.current_quantity < quantity:  # 检查库存
            response = {
                "type": "tool",
                "action": "borrow_tool",
                "success": False,
                "message": f"库存不足，当前剩余: {tool.current_quantity}个",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(response, websocket)
            return

        # 记录借出前的库存
        old_quantity = tool.current_quantity

        # 减少库存
        tool.current_quantity -= quantity

        # 更新状态
        if tool.current_quantity <= 0:
            tool.status = "无库存"
        elif tool.current_quantity <= tool.threshold:
            tool.status = "低库存"
        else:
            tool.status = "正常"

        # 更新时间
        tool.last_updated = datetime.now()

        db.commit()  # 提交事务

        logger.info(f"工具借出: 数量{quantity}个, 库存: {old_quantity}->{tool.current_quantity}")

        # 记录借出时间（调用B同学的函数）
        try:
            create_borrow_record(db, quantity)  # 创建借出记录
        except Exception as e:
            logger.error(f"记录借出时间失败: {e}")

        # 准备响应
        response = {
            "type": "tool",
            "action": "borrow_tool",
            "success": True,
            "data": {
                "borrowed_quantity": quantity,
                "remaining_quantity": tool.current_quantity,
                "status": tool.status,
                "borrow_time": datetime.now().isoformat()  # 借出时间
            },
            "message": "借出成功",
            "timestamp": datetime.now().isoformat()
        }

        await manager.send_personal_message(response, websocket)  # 发送响应

        # 广播库存变化
        broadcast_msg = {
            "type": "notification",
            "action": "inventory_changed",
            "data": {
                "old_quantity": old_quantity,
                "new_quantity": tool.current_quantity,
                "status": tool.status,
                "timestamp": datetime.now().isoformat()
            }
        }
        await manager.broadcast(broadcast_msg)  # 广播消息

    except Exception as e:
        logger.error(f"借出工具时出错: {e}")
        error_response = {
            "type": "error",
            "action": "borrow_tool",
            "message": f"借出失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(error_response, websocket)
    finally:
        db.close()  # 关闭数据库会话


async def return_tool(websocket: WebSocket, message: dict):
    """
    归还工具

    参数:
    - websocket: WebSocket连接对象
    - message: 消息字典
    """
    db = SessionLocal()  # 创建数据库会话
    try:
        quantity = message.get("quantity", 1)  # 获取归还数量

        if quantity <= 0:  # 验证数量
            response = {
                "type": "tool",
                "action": "return_tool",
                "success": False,
                "message": "归还数量必须大于0",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(response, websocket)
            return

        tool = db.query(Tool).filter(Tool.id == 1).first()  # 查询工具

        if not tool:  # 工具不存在
            response = {
                "type": "tool",
                "action": "return_tool",
                "success": False,
                "message": "工具不存在",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(response, websocket)
            return

        if tool.current_quantity + quantity > tool.total_quantity:  # 检查是否会超过总量
            response = {
                "type": "tool",
                "action": "return_tool",
                "success": False,
                "message": f"归还后超过总量，当前: {tool.current_quantity}, 总量: {tool.total_quantity}",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(response, websocket)
            return

        # 记录归还前的库存
        old_quantity = tool.current_quantity

        # 增加库存
        tool.current_quantity += quantity

        # 更新状态
        if tool.current_quantity <= 0:
            tool.status = "无库存"
        elif tool.current_quantity <= tool.threshold:
            tool.status = "低库存"
        else:
            tool.status = "正常"

        # 更新时间
        tool.last_updated = datetime.now()

        db.commit()  # 提交事务

        logger.info(f"工具归还: 数量{quantity}个, 库存: {old_quantity}->{tool.current_quantity}")

        # 记录归还时间（调用B同学的函数）
        try:
            create_return_record(db, quantity)  # 创建归还记录
        except Exception as e:
            logger.error(f"记录归还时间失败: {e}")

        # 准备响应
        response = {
            "type": "tool",
            "action": "return_tool",
            "success": True,
            "data": {
                "returned_quantity": quantity,
                "current_quantity": tool.current_quantity,
                "status": tool.status,
                "return_time": datetime.now().isoformat()  # 归还时间
            },
            "message": "归还成功",
            "timestamp": datetime.now().isoformat()
        }

        await manager.send_personal_message(response, websocket)  # 发送响应

        # 广播库存变化
        broadcast_msg = {
            "type": "notification",
            "action": "inventory_changed",
            "data": {
                "old_quantity": old_quantity,
                "new_quantity": tool.current_quantity,
                "status": tool.status,
                "timestamp": datetime.now().isoformat()
            }
        }
        await manager.broadcast(broadcast_msg)  # 广播消息

    except Exception as e:
        logger.error(f"归还工具时出错: {e}")
        error_response = {
            "type": "error",
            "action": "return_tool",
            "message": f"归还失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(error_response, websocket)
    finally:
        db.close()  # 关闭数据库会话


async def sensor_update(websocket: WebSocket, message: dict):
    """
    传感器数据更新

    参数:
    - websocket: WebSocket连接对象
    - message: 消息字典
    """
    db = SessionLocal()  # 创建数据库会话
    try:
        current_weight = message.get("current_weight")  # 获取重量数据

        if current_weight is None:  # 检查参数
            response = {
                "type": "tool",
                "action": "sensor_update",
                "success": False,
                "message": "缺少current_weight参数",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(response, websocket)
            return

        tool = db.query(Tool).filter(Tool.id == 1).first()  # 查询工具

        if not tool:  # 工具不存在
            response = {
                "type": "tool",
                "action": "sensor_update",
                "success": False,
                "message": "工具不存在",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(response, websocket)
            return

        # 防止除零错误
        if tool.unit_weight <= 0:
            tool.unit_weight = 100.0

        # 根据重量计算库存数量
        estimated_quantity = int(current_weight / tool.unit_weight)

        # 记录更新前的库存
        old_quantity = tool.current_quantity

        # 更新库存数量
        tool.current_quantity = estimated_quantity

        # 限制数量范围
        if tool.current_quantity < 0:
            tool.current_quantity = 0
        elif tool.current_quantity > tool.total_quantity:
            tool.current_quantity = tool.total_quantity

        # 更新状态
        if tool.current_quantity <= 0:
            tool.status = "无库存"
        elif tool.current_quantity <= tool.threshold:
            tool.status = "低库存"
        else:
            tool.status = "正常"

        # 更新时间
        tool.last_updated = datetime.now()

        db.commit()  # 提交事务

        logger.info(
            f"传感器更新: 重量{current_weight}g -> 数量{estimated_quantity}, 库存: {old_quantity}->{tool.current_quantity}")

        response = {
            "type": "tool",
            "action": "sensor_update",
            "success": True,
            "data": {
                "current_weight": current_weight,
                "estimated_quantity": estimated_quantity,
                "current_quantity": tool.current_quantity,
                "status": tool.status
            },
            "message": "传感器数据已更新",
            "timestamp": datetime.now().isoformat()
        }

        await manager.send_personal_message(response, websocket)  # 发送响应

        # 如果库存变化，广播通知
        if old_quantity != tool.current_quantity:
            broadcast_msg = {
                "type": "notification",
                "action": "inventory_changed",
                "data": {
                    "old_quantity": old_quantity,
                    "new_quantity": tool.current_quantity,
                    "status": tool.status,
                    "timestamp": datetime.now().isoformat()
                }
            }
            await manager.broadcast(broadcast_msg)  # 广播消息

    except Exception as e:
        logger.error(f"传感器更新时出错: {e}")
        error_response = {
            "type": "error",
            "action": "sensor_update",
            "message": f"传感器更新失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(error_response, websocket)
    finally:
        db.close()  # 关闭数据库会话