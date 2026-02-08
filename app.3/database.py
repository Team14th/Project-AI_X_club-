"""
数据库配置
版本: 2.0
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# 数据库文件路径
DATABASE_URL = "sqlite:///./tool_system.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 需要这个参数
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库初始化完成")
