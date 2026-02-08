"""
数据模型定义
功能：
1. 工具表
2. 员工表
3. 借还记录表
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
from app.database import Base  # 数据库基类

# ---------------- 工具表 ----------------
class Tool(Base):
    """工具表模型 - 管理库存状态"""
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, default=1)
    name = Column(String(100), default="车间通用工具")
    total_quantity = Column(Integer, default=10)
    current_quantity = Column(Integer, default=10)
    threshold = Column(Integer, default=2)
    unit_weight = Column(Float, default=100.0)
    status = Column(String(20), default="正常")
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ---------------- 员工表 ----------------
class Employee(Base):
    """员工表模型"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, default=1)
    name = Column(String(50), default="唯一员工")
    employee_id = Column(String(20), default="EMP001")
    face_id = Column(String(100), default="face_001")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# ---------------- 借还记录表 ----------------
class BorrowRecord(Base):
    """借还记录表"""
    __tablename__ = "borrow_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, default=1)
    tool_id = Column(Integer, default=1)
    action = Column(String(10), nullable=False)  # 借出/归还
    quantity = Column(Integer, default=1)
    borrow_time = Column(DateTime, nullable=False)
    return_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
