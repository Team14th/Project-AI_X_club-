"""
WebSocket 服务器 - 支持双硬件协作与授权窗口机制
版本: 2.0
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect

# 授权窗口配置
AUTH_WINDOW_TIMEOUT = 30  # 授权窗口有效期（秒）


class AuthorizationWindow:
    """授权窗口：记录人脸识别成功后的有效操作时间窗口"""
    
    def __init__(self, user: str, device_id: str):
        self.user = user
        self.device_id = device_id
        self.start_time = datetime.now()
        self.is_active = True
    
    def is_valid(self) -> bool:
        """检查授权窗口是否仍然有效"""
        if not self.is_active:
            return False
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed < AUTH_WINDOW_TIMEOUT
    
    def close(self):
        """关闭授权窗口"""
        self.is_active = False


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.hardware_connections: Dict[str, WebSocket] = {}  # device_id -> WebSocket
        self.frontend_connections: list[WebSocket] = []
        self.unidentified_connections: Dict[WebSocket, dict] = {}
        
        # 授权窗口管理
        self.active_auth_window: Optional[AuthorizationWindow] = None
    
    async def connect(self, websocket: WebSocket):
        """接受新的 WebSocket 连接"""
        await websocket.accept()
        self.unidentified_connections[websocket] = {"connected_at": datetime.now()}
        print(f"✓ 新连接已建立，等待身份识别...")
    
    async def identify(self, websocket: WebSocket, role: str, client_info: dict):
        """识别客户端身份"""
        if websocket not in self.unidentified_connections:
            return
        
        del self.unidentified_connections[websocket]
        
        if role == "hardware":
            device_id = client_info.get("device_id", "unknown")
            self.hardware_connections[device_id] = websocket
            print(f"✓ 硬件端已识别 (device_id: {device_id})")
            print(f"  当前硬件连接数: {len(self.hardware_connections)}")
            
            # 发送识别确认
            response = {
                "type": "identify_ack",
                "status": "ok",
                "role": "hardware",
                "device_id": device_id,
                "message": "身份识别成功"
            }
            await websocket.send_text(json.dumps(response))
            
        elif role == "frontend":
            self.frontend_connections.append(websocket)
            print(f"✓ 前端已识别")
            print(f"  当前前端连接数: {len(self.frontend_connections)}")
            
            # 发送识别确认
            response = {
                "type": "identify_ack",
                "status": "ok",
                "role": "frontend",
                "message": "身份识别成功"
            }
            await websocket.send_text(json.dumps(response))
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        # 从硬件连接中移除
        device_id_to_remove = None
        for device_id, ws in self.hardware_connections.items():
            if ws == websocket:
                device_id_to_remove = device_id
                break
        if device_id_to_remove:
            del self.hardware_connections[device_id_to_remove]
            print(f"✗ 硬件端已断开 (device_id: {device_id_to_remove})")
        
        # 从前端连接中移除
        if websocket in self.frontend_connections:
            self.frontend_connections.remove(websocket)
            print(f"✗ 前端已断开")
        
        # 从未识别连接中移除
        if websocket in self.unidentified_connections:
            del self.unidentified_connections[websocket]
    
    async def send_to_hardware(self, device_id: str, message: dict):
        """向指定硬件设备发送消息"""
        if device_id in self.hardware_connections:
            try:
                await self.hardware_connections[device_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"向硬件 {device_id} 发送消息失败: {e}")
    
    async def broadcast_to_frontend(self, message: dict):
        """向所有前端广播消息"""
        disconnected = []
        for connection in self.frontend_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                print(f"向前端广播失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            if conn in self.frontend_connections:
                self.frontend_connections.remove(conn)
    
    # ==================== 授权窗口管理 ====================
    
    def start_auth_window(self, user: str, device_id: str) -> bool:
        """开启授权窗口"""
        if self.active_auth_window and self.active_auth_window.is_valid():
            print(f"⚠️ 已存在有效的授权窗口，拒绝新的授权请求")
            return False
        
        self.active_auth_window = AuthorizationWindow(user, device_id)
        print(f"✓ 授权窗口已开启: user={user}, device_id={device_id}, 有效期={AUTH_WINDOW_TIMEOUT}秒")
        return True
    
    def check_auth_window(self) -> Optional[str]:
        """检查当前是否有有效的授权窗口，返回授权用户名"""
        if self.active_auth_window and self.active_auth_window.is_valid():
            return self.active_auth_window.user
        return None
    
    def close_auth_window(self):
        """关闭授权窗口"""
        if self.active_auth_window:
            self.active_auth_window.close()
            print(f"✓ 授权窗口已关闭")
            self.active_auth_window = None


# 全局连接管理器实例
manager = ConnectionManager()


async def handle_hardware_message(websocket: WebSocket, message: dict, device_id: str):
    """处理硬件端发送的消息"""
    from record_handler import handle_borrow_event, handle_return_event, handle_failure_alarm
    
    msg_type = message.get("type")
    
    # ==================== 1. 授权请求 (来自人脸板) ====================
    if msg_type == "auth_request":
        user = message.get("user", "未知用户")
        
        # 开启授权窗口
        success = manager.start_auth_window(user, device_id)
        
        if success:
            # 向人脸板发送开门指令
            response = {
                "type": "command",
                "command": "open_door",
                "user": user
            }
            await manager.send_to_hardware(device_id, response)
            
            # 启动授权窗口超时任务
            asyncio.create_task(auth_window_timeout_task(device_id))
        else:
            # 授权失败（已有其他用户在操作）
            response = {
                "type": "error",
                "message": "当前有其他用户正在操作，请稍后再试"
            }
            await manager.send_to_hardware(device_id, response)
    
    # ==================== 2. 借出事件 (来自重量板) ====================
    elif msg_type == "hardware_event" and message.get("event") == "borrow":
        # 检查授权窗口
        authorized_user = manager.check_auth_window()
        
        if authorized_user:
            count = message.get("count", 0)
            
            # 调用借出处理逻辑
            record_id, inventory_left = await handle_borrow_event(authorized_user, count)
            
            # 向重量板发送响应
            response = {
                "type": "hardware_response",
                "event": "borrow",
                "status": "ok",
                "record_id": record_id,
                "message": "借出成功"
            }
            await manager.send_to_hardware(device_id, response)
            
            # 向所有前端广播借出事件
            broadcast_message = {
                "type": "borrow",
                "record_id": record_id,
                "user": authorized_user,
                "count": count,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "inventory_left": inventory_left
            }
            await manager.broadcast_to_frontend(broadcast_message)
            
            print(f"✓ 借出事件已处理: user={authorized_user}, count={count}, record_id={record_id}")
        else:
            # 无有效授权窗口，拒绝操作
            response = {
                "type": "error",
                "message": "未授权的操作，请先进行人脸识别"
            }
            await manager.send_to_hardware(device_id, response)
            print(f"⚠️ 拒绝未授权的借出操作 (device_id: {device_id})")
    
    # ==================== 3. 归还事件 (来自重量板) ====================
    elif msg_type == "hardware_event" and message.get("event") == "return":
        # 检查授权窗口
        authorized_user = manager.check_auth_window()
        
        if authorized_user:
            record_id = message.get("record_id")
            count = message.get("count", 0)
            
            # 调用归还处理逻辑
            inventory_left = await handle_return_event(record_id, count)
            
            # 向重量板发送响应
            response = {
                "type": "hardware_response",
                "event": "return",
                "status": "ok",
                "message": "归还成功"
            }
            await manager.send_to_hardware(device_id, response)
            
            # 向所有前端广播归还事件
            broadcast_message = {
                "type": "return",
                "record_id": record_id,
                "user": authorized_user,
                "count": count,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "inventory_left": inventory_left
            }
            await manager.broadcast_to_frontend(broadcast_message)
            
            print(f"✓ 归还事件已处理: record_id={record_id}, count={count}")
            
            # 关闭授权窗口
            manager.close_auth_window()
            
            # 向人脸板发送关门指令
            face_device_id = manager.active_auth_window.device_id if manager.active_auth_window else None
            if face_device_id:
                close_command = {"type": "command", "command": "close_door"}
                await manager.send_to_hardware(face_device_id, close_command)
        else:
            # 无有效授权窗口，拒绝操作
            response = {
                "type": "error",
                "message": "未授权的操作，请先进行人脸识别"
            }
            await manager.send_to_hardware(device_id, response)
            print(f"⚠️ 拒绝未授权的归还操作 (device_id: {device_id})")
    
    # ==================== 4. 失败报警 (来自人脸板) ====================
    elif msg_type == "hardware_event" and message.get("event") == "failure_alarm":
        reason = message.get("reason", "未知原因")
        details = message.get("details", "")
        
        # 调用失败报警处理逻辑
        alarm_id = await handle_failure_alarm(reason, details)
        
        # 向人脸板发送响应
        response = {
            "type": "hardware_response",
            "event": "failure_alarm",
            "status": "ok",
            "alarm_id": alarm_id,
            "message": "报警已记录"
        }
        await manager.send_to_hardware(device_id, response)
        
        # 向所有前端广播失败报警
        broadcast_message = {
            "type": "failure_alarm",
            "alarm_id": alarm_id,
            "reason": reason,
            "details": details,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        await manager.broadcast_to_frontend(broadcast_message)
        
        print(f"✓ 失败报警已处理: reason={reason}")
    
    else:
        print(f"⚠️ 收到未知类型的硬件消息: {msg_type}")


async def auth_window_timeout_task(face_device_id: str):
    """授权窗口超时任务"""
    await asyncio.sleep(AUTH_WINDOW_TIMEOUT)
    
    # 检查授权窗口是否仍然有效
    if manager.active_auth_window and manager.active_auth_window.is_valid():
        print(f"⏰ 授权窗口超时，自动关闭")
        manager.close_auth_window()
        
        # 向人脸板发送关门指令
        close_command = {"type": "command", "command": "close_door"}
        await manager.send_to_hardware(face_device_id, close_command)


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 主入口"""
    await manager.connect(websocket)
    
    device_id = None
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            # 处理身份识别
            if msg_type == "identify":
                role = message.get("role")
                client_info = message
                await manager.identify(websocket, role, client_info)
                
                if role == "hardware":
                    device_id = message.get("device_id", "unknown")
                
                # 如果是前端，发送 init 消息
                if role == "frontend":
                    from record_handler import get_init_data
                    init_data = await get_init_data()
                    await websocket.send_text(json.dumps(init_data))
            
            # 处理硬件消息
            elif msg_type in ["auth_request", "hardware_event"]:
                if device_id:
                    await handle_hardware_message(websocket, message, device_id)
                else:
                    error_response = {
                        "type": "error",
                        "message": "请先完成身份识别"
                    }
                    await websocket.send_text(json.dumps(error_response))
            
            else:
                print(f"⚠️ 收到未知类型的消息: {msg_type}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 错误: {e}")
        manager.disconnect(websocket)
