"""
数据库配置文件
功能：创建SQLite数据库连接
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite数据库文件路径
SQLALCHEMY_DATABASE_URL = "sqlite:///./tool_hybrid.db"

# 创建数据库引擎，connect_args是SQLite专用参数
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite需要这个参数才能多线程访问
)

# 创建会话工厂，用于生成数据库会话对象
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建声明性基类，所有数据模型都继承这个类
Base = declarative_base()

def get_db():
    """
    获取数据库会话的依赖函数
    每次请求时创建一个新会话，请求结束后自动关闭
    """
    db = SessionLocal()  # 创建新的数据库会话
    try:
        yield db  # 将会话提供给调用者使用
    finally:
        db.close()  # 使用完毕后关闭会话