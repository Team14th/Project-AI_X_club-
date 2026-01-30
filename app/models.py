"""
数据模型定义 - 工具表部分
功能：定义唯一的工具表结构
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
from app.database import Base  # 从database.py导入Base基类


class Tool(Base):
    """工具表模型 - 只有一种工具，管理库存状态"""
    __tablename__ = "tools"  # 数据库表名

    # 主键，固定为1，因为整个系统只有一种工具
    id = Column(Integer, primary_key=True, default=1)

    # 工具名称
    name = Column(String(100), default="车间通用工具")

    # 总库存数量，默认10个
    total_quantity = Column(Integer, default=10)

    # 当前库存数量，初始等于总数
    current_quantity = Column(Integer, default=10)

    # 预警阈值，低于2个时会报警
    threshold = Column(Integer, default=2)

    # 单个工具的标准重量（克），用于根据传感器重量计算数量
    unit_weight = Column(Float, default=100.0)

    # 工具状态：正常/低库存/无库存
    status = Column(String(20), default="正常")

    # 最后更新时间，自动记录每次库存变化的时间
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)



###########################员工和工具功能管理分界线################################




    """
    数据模型定义 - 员工表和记录表部分
    功能：1. 定义唯一的员工 2. 定义借还记录表
    """
    from sqlalchemy import Column, Integer, String, DateTime, Boolean # noqa
    from datetime import datetime # noqa:401
    from .database import Base  # 从database.py导入Base基类 # noqa:401

    class Employee(Base):
        """员工表模型 - 只有1个员工"""
        __tablename__ = "employees"  # 数据库表名

        # 主键，固定为1，因为只有1个员工
        id = Column(Integer, primary_key=True, default=1)

        # 员工姓名
        name = Column(String(50), default="唯一员工")

        # 员工编号
        employee_id = Column(String(20), default="EMP001")

        # 人脸识别ID，硬件识别后得到这个值
        face_id = Column(String(100), default="face_001")

        # 是否在职，默认为True（在职）
        is_active = Column(Boolean, default=True)

        # 创建时间
        created_at = Column(DateTime, default=datetime.now)

    class BorrowRecord(Base):
        """借还记录表 - 记录每次借出和归还的时间"""
        __tablename__ = "borrow_records"  # 数据库表名

        # 主键，自动递增
        id = Column(Integer, primary_key=True, index=True)

        # 员工ID，固定为1
        employee_id = Column(Integer, default=1)

        # 工具ID，固定为1
        tool_id = Column(Integer, default=1)

        # 操作类型：借出/归还
        action = Column(String(10), nullable=False)

        # 数量
        quantity = Column(Integer, default=1)

        # 借出时间
        borrow_time = Column(DateTime, nullable=False)

        # 归还时间（借出时为空）
        return_time = Column(DateTime, nullable=True)

        # 记录创建时间
        created_at = Column(DateTime, default=datetime.now)