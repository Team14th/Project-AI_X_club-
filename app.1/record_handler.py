"""
记录处理模块
作者：B同学
功能：1. 创建借还记录 2. 查询记录函数
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional

# 导入数据库和模型
from app.database import SessionLocal
from app.models import BorrowRecord, Employee

# 设置日志记录器
logger = logging.getLogger(__name__)


# 初始化员工数据
def init_employee():
    """
    初始化员工数据
    在服务器启动时自动创建唯一的员工
    """
    db = SessionLocal()  # 创建数据库会话
    try:
        employee = db.query(Employee).filter(Employee.id == 1).first()  # 查询员工

        if not employee:  # 如果没有员工，创建默认员工
            employee = Employee(
                name="唯一员工",  # 员工姓名
                employee_id="EMP001",  # 员工编号
                face_id="face_001",  # 人脸ID
                is_active=True  # 在职状态
            )
            db.add(employee)  # 添加到会话
            db.commit()  # 提交到数据库
            logger.info("员工数据初始化完成")
    finally:
        db.close()  # 关闭数据库会话


# 记录创建函数（供A同学调用）
def create_borrow_record(db: Session, quantity: int = 1) -> BorrowRecord:
    """
    创建借出记录
    在工具借出成功后调用，记录借出时间

    参数:
    - db: 数据库会话
    - quantity: 借出数量

    返回: 创建的记录对象
    """
    try:
        # 创建借出记录
        record = BorrowRecord(
            employee_id=1,  # 员工ID固定为1
            tool_id=1,  # 工具ID固定为1
            action="借出",  # 操作类型
            quantity=quantity,  # 借出数量
            borrow_time=datetime.now(),  # 借出时间
            return_time=None  # 归还时间为空
        )

        db.add(record)  # 添加到会话
        db.commit()  # 提交到数据库
        db.refresh(record)  # 刷新获取ID

        logger.info(f"记录借出: 数量{quantity}个, 时间{record.borrow_time}")

        return record

    except Exception as e:
        logger.error(f"创建借出记录失败: {e}")
        raise


def create_return_record(db: Session, quantity: int = 1) -> Optional[BorrowRecord]:
    """
    创建归还记录
    在工具归还成功后调用，记录归还时间

    参数:
    - db: 数据库会话
    - quantity: 归还数量

    返回: 更新的记录对象
    """
    try:
        # 查找最近的借出记录（未归还的）
        borrow_record = db.query(BorrowRecord).filter(
            BorrowRecord.action == "借出",  # 借出记录
            BorrowRecord.return_time.is_(None)  # 未归还
        ).order_by(BorrowRecord.borrow_time.desc()).first()  # 按时间倒序，取最近的

        if borrow_record:
            # 更新归还时间
            borrow_record.return_time = datetime.now()
            borrow_record.action = "归还"  # 更新动作为归还

            db.commit()  # 提交到数据库
            db.refresh(borrow_record)  # 刷新获取最新数据

            logger.info(f"记录归还: 数量{quantity}个, 时间{borrow_record.return_time}")

            return borrow_record

        else:
            # 如果没有找到借出记录，创建新记录
            record = BorrowRecord(
                employee_id=1,  # 员工ID固定为1
                tool_id=1,  # 工具ID固定为1
                action="归还",  # 操作类型
                quantity=quantity,  # 归还数量
                borrow_time=datetime.now(),  # 借出时间
                return_time=datetime.now()  # 归还时间
            )

            db.add(record)  # 添加到会话
            db.commit()  # 提交到数据库
            db.refresh(record)  # 刷新获取ID

            logger.warning(f"创建新归还记录: 数量{quantity}个")

            return record

    except Exception as e:
        logger.error(f"创建归还记录失败: {e}")
        raise


# 记录查询函数
def get_all_records(db: Session, skip: int = 0, limit: int = 100) -> List[BorrowRecord]:
    """
    获取所有借还记录

    参数:
    - db: 数据库会话
    - skip: 跳过的记录数
    - limit: 返回的最大记录数

    返回: 记录列表
    """
    records = db.query(BorrowRecord).order_by(BorrowRecord.borrow_time.desc()).offset(skip).limit(limit).all()
    return records


def get_current_borrow(db: Session) -> Optional[BorrowRecord]:
    """
    获取当前借出未还的记录

    参数:
    - db: 数据库会话

    返回: 当前借出记录（如果存在）
    """
    record = db.query(BorrowRecord).filter(
        BorrowRecord.action == "借出",  # 借出记录
        BorrowRecord.return_time.is_(None)  # 未归还
    ).order_by(BorrowRecord.borrow_time.desc()).first()  # 按时间倒序，取最近的

    return record


def get_statistics(db: Session) -> dict:
    """
    获取统计信息

    参数:
    - db: 数据库会话

    返回: 统计信息字典
    """
    # 计算今日开始时间
    today_start = datetime.combine(datetime.now().date(), datetime.min.time())

    # 查询今日借出次数
    today_borrows = db.query(BorrowRecord).filter(
        BorrowRecord.action == "借出",  # 借出记录
        BorrowRecord.borrow_time >= today_start  # 今日之后
    ).count()

    # 查询今日归还次数
    today_returns = db.query(BorrowRecord).filter(
        BorrowRecord.action == "归还",  # 归还记录
        BorrowRecord.borrow_time >= today_start  # 今日之后
    ).count()

    # 查询总借出次数
    total_borrows = db.query(BorrowRecord).filter(
        BorrowRecord.action == "借出"  # 借出记录
    ).count()

    # 查询总归还次数
    total_returns = db.query(BorrowRecord).filter(
        BorrowRecord.action == "归还"  # 归还记录
    ).count()

    # 返回统计信息
    return {
        "today_borrows": today_borrows,
        "today_returns": today_returns,
        "total_borrows": total_borrows,
        "total_returns": total_returns
    }