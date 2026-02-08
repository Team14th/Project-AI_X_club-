"""
数据库模型定义
版本: 2.0
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class BorrowRecord(Base):
    """
    借还记录表 (事件流模型)
    每次借出和归还都是一条独立的记录,通过 record_id 关联
    """
    __tablename__ = "borrow_records"

    # 数据库主键 (自增)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 业务唯一ID (用于关联借出和归还)
    record_id = Column(String(50), index=True, nullable=False, comment="业务记录ID,格式: rec_时间戳_随机数")
    
    # 事件类型
    type = Column(String(20), nullable=False, comment="事件类型: borrow 或 return")
    
    # 用户信息
    user = Column(String(100), nullable=False, comment="借用人姓名")
    
    # 数量
    count = Column(Integer, nullable=False, comment="借出/归还数量")
    
    # 事件发生时间
    time = Column(DateTime, nullable=False, default=datetime.now, comment="事件发生时间")
    
    # 事件发生后的剩余库存
    inventory_left = Column(Integer, nullable=False, comment="事件后的剩余库存")
    
    # 创建时间 (数据库记录创建时间)
    created_at = Column(DateTime, default=datetime.now, comment="记录创建时间")


class FailureAlarm(Base):
    """
    失败报警记录表
    记录人脸识别失败等异常事件
    """
    __tablename__ = "failure_alarms"

    # 数据库主键 (自增)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 报警唯一ID
    alarm_id = Column(String(50), index=True, nullable=False, comment="报警ID,格式: alm_时间戳_随机数")
    
    # 报警原因
    reason = Column(String(200), nullable=False, comment="报警原因,如: 人脸识别失败")
    
    # 详细信息
    details = Column(String(500), nullable=True, comment="详细描述")
    
    # 报警时间
    timestamp = Column(DateTime, nullable=False, default=datetime.now, comment="报警发生时间")
    
    # 是否已处理
    is_handled = Column(Boolean, default=False, comment="是否已处理")
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.now, comment="记录创建时间")


class InventoryConfig(Base):
    """
    库存配置表
    记录工具的总量和当前剩余量
    """
    __tablename__ = "inventory_config"

    # 数据库主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 总库存
    total_inventory = Column(Integer, nullable=False, comment="工具总数量")
    
    # 当前剩余库存
    current_inventory = Column(Integer, nullable=False, comment="当前剩余数量")
    
    # 更新时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="最后更新时间")
