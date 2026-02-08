"""
借还记录和报警处理逻辑
版本: 2.0
"""

import uuid
from datetime import datetime
from database import SessionLocal
from models import BorrowRecord, FailureAlarm, InventoryConfig


# ==================== 库存管理 ====================

async def get_current_inventory() -> int:
    """获取当前库存数量"""
    db = SessionLocal()
    try:
        config = db.query(InventoryConfig).first()
        if not config:
            # 如果没有配置，创建默认配置
            config = InventoryConfig(total_inventory=50, current_inventory=50)
            db.add(config)
            db.commit()
            db.refresh(config)
        return config.current_inventory
    finally:
        db.close()


async def update_inventory(delta: int) -> int:
    """更新库存数量，返回更新后的库存"""
    db = SessionLocal()
    try:
        config = db.query(InventoryConfig).first()
        if not config:
            config = InventoryConfig(total_inventory=50, current_inventory=50)
            db.add(config)
        
        config.current_inventory += delta
        db.commit()
        db.refresh(config)
        return config.current_inventory
    finally:
        db.close()


# ==================== 借出事件处理 ====================

async def handle_borrow_event(user: str, count: int) -> tuple[str, int]:
    """
    处理借出事件
    返回: (record_id, inventory_left)
    """
    db = SessionLocal()
    try:
        # 生成唯一的 record_id
        record_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # 更新库存
        inventory_left = await update_inventory(-count)
        
        # 创建借出记录
        borrow_record = BorrowRecord(
            record_id=record_id,
            type="borrow",
            user=user,
            count=count,
            time=datetime.now(),
            inventory_left=inventory_left
        )
        db.add(borrow_record)
        db.commit()
        
        return record_id, inventory_left
    finally:
        db.close()


# ==================== 归还事件处理 ====================

async def handle_return_event(record_id: str, count: int) -> int:
    """
    处理归还事件
    返回: inventory_left
    """
    db = SessionLocal()
    try:
        # 更新库存
        inventory_left = await update_inventory(count)
        
        # 创建归还记录
        return_record = BorrowRecord(
            record_id=record_id,
            type="return",
            user="",  # 归还时用户信息从借出记录中获取
            count=count,
            time=datetime.now(),
            inventory_left=inventory_left
        )
        db.add(return_record)
        db.commit()
        
        return inventory_left
    finally:
        db.close()


# ==================== 失败报警处理 ====================

async def handle_failure_alarm(reason: str, details: str) -> str:
    """
    处理失败报警事件
    返回: alarm_id
    """
    db = SessionLocal()
    try:
        # 生成唯一的 alarm_id
        alarm_id = f"alm_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # 创建报警记录
        alarm = FailureAlarm(
            alarm_id=alarm_id,
            reason=reason,
            details=details,
            timestamp=datetime.now()
        )
        db.add(alarm)
        db.commit()
        
        return alarm_id
    finally:
        db.close()


# ==================== 初始化数据 ====================

async def get_init_data() -> dict:
    """
    获取前端初始化数据
    """
    db = SessionLocal()
    try:
        # 获取库存配置
        config = db.query(InventoryConfig).first()
        if not config:
            config = InventoryConfig(total_inventory=50, current_inventory=50)
            db.add(config)
            db.commit()
            db.refresh(config)
        
        # 获取所有未归还的借出记录
        active_records = db.query(BorrowRecord).filter(
            BorrowRecord.type == "borrow"
        ).all()
        
        # 检查哪些借出记录已经归还
        active_records_data = []
        for borrow in active_records:
            # 查找对应的归还记录
            return_record = db.query(BorrowRecord).filter(
                BorrowRecord.record_id == borrow.record_id,
                BorrowRecord.type == "return"
            ).first()
            
            if not return_record:
                # 未归还的记录
                active_records_data.append({
                    "record_id": borrow.record_id,
                    "user": borrow.user,
                    "count": borrow.count,
                    "time": borrow.time.strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return {
            "type": "init",
            "tool_name": "通用工具",
            "total_inventory": config.total_inventory,
            "current_inventory": config.current_inventory,
            "active_records": active_records_data
        }
    finally:
        db.close()
