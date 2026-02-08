"""
HTTP服务器模块
功能：1. 提供HTTP查询接口 2. 返回JSON格式数据
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

# 导入数据库和模型
from app.database import get_db
from app.models import BorrowRecord
from app.record_handler import get_all_records, get_current_borrow, get_statistics

# 创建FastAPI应用
app = FastAPI(
    title="工具柜历史记录API",
    version="1.0.0",
    description="提供历史记录查询的HTTP接口"
)

# 配置CORS（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,  # 允许凭据
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有HTTP头
)


# API端点1：获取所有记录
@app.get("/api/records", response_model=List[dict])
def get_records(
        skip: int = 0,  # 跳过的记录数，用于分页
        limit: int = 100,  # 返回的最大记录数
        db: Session = Depends(get_db)  # 自动注入数据库会话
):
    """
    获取所有借还记录

    参数:
    - skip: 跳过的记录数（默认0）
    - limit: 返回的最大记录数（默认100）

    返回: JSON格式的记录列表
    """
    try:
        records = get_all_records(db, skip, limit)  # 调用查询函数

        # 格式化记录数据
        formatted_records = []
        for record in records:
            formatted_records.append({
                "id": record.id,
                "employee_id": record.employee_id,
                "tool_id": record.tool_id,
                "action": record.action,
                "quantity": record.quantity,
                "borrow_time": record.borrow_time.isoformat() if record.borrow_time else None,
                "return_time": record.return_time.isoformat() if record.return_time else None,
                "created_at": record.created_at.isoformat() if record.created_at else None
            })

        return formatted_records  # 返回JSON响应

    except Exception as e:
        # 处理错误
        raise HTTPException(status_code=500, detail=f"获取记录失败: {str(e)}")


# API端点2：获取当前借出记录
@app.get("/api/records/current", response_model=dict)
def get_current_record(db: Session = Depends(get_db)):
    """
    获取当前借出未还的记录

    返回: JSON格式的当前借出信息
    """
    try:
        record = get_current_borrow(db)  # 调用查询函数

        if record:
            # 有未归还的工具
            return {
                "is_borrowed": True,
                "record": {
                    "id": record.id,
                    "borrow_time": record.borrow_time.isoformat() if record.borrow_time else None,
                    "quantity": record.quantity,
                    "duration_seconds": int(
                        (datetime.now() - record.borrow_time).total_seconds()) if record.borrow_time else 0
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 没有未归还的工具
            return {
                "is_borrowed": False,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        # 处理错误
        raise HTTPException(status_code=500, detail=f"获取当前记录失败: {str(e)}")


# API端点3：获取统计信息
@app.get("/api/records/stats", response_model=dict)
def get_record_stats(db: Session = Depends(get_db)):
    """
    获取统计信息

    返回: JSON格式的统计信息
    """
    try:
        stats = get_statistics(db)  # 调用统计函数

        return {
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 处理错误
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


# 根路径
@app.get("/")
def root():
    """
    根路径，返回API信息

    返回: JSON格式的API信息
    """
    return {
        "service": "工具柜历史记录API",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/api/records", "method": "GET", "description": "获取所有记录"},
            {"path": "/api/records/current", "method": "GET", "description": "获取当前借出记录"},
            {"path": "/api/records/stats", "method": "GET", "description": "获取统计信息"}
        ],
        "timestamp": datetime.now().isoformat()
    }