"""
太玄智译 - 数据库连接与会话管理
使用 SQLAlchemy 2.0 异步风格（同步版本，适配桌面应用）
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from taixuan_translator.core.config import get_settings
from taixuan_translator.data.models import Base

# 全局引擎和会话工厂
_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def _configure_sqlite(dbapi_connection: object, connection_record: object) -> None:
    """SQLite性能优化配置"""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    # WAL模式：提升并发读写性能
    cursor.execute("PRAGMA journal_mode=WAL")
    # 同步模式：NORMAL（平衡性能与安全）
    cursor.execute("PRAGMA synchronous=NORMAL")
    # 缓存大小：64MB
    cursor.execute("PRAGMA cache_size=-65536")
    # 外键约束
    cursor.execute("PRAGMA foreign_keys=ON")
    # 临时表存内存
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


def get_engine() -> Engine:
    """获取数据库引擎（单例）"""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_path = settings.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        db_url = f"sqlite:///{db_path}"
        _engine = create_engine(
            db_url,
            echo=settings.debug,
            connect_args={
                "check_same_thread": False,  # 允许多线程访问
                "timeout": 30,
            },
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

        # 注册SQLite优化配置
        event.listen(_engine, "connect", _configure_sqlite)

        logger.info(f"数据库引擎初始化完成: {db_path}")
    return _engine


def get_session_factory() -> sessionmaker:
    """获取会话工厂（单例）"""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=True,
            expire_on_commit=False,  # 提交后不过期，避免额外查询
        )
    return _SessionFactory


def init_database() -> None:
    """初始化数据库（创建所有表）"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("数据库表结构初始化完成")


def drop_all_tables() -> None:
    """删除所有表（仅用于测试）"""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    logger.warning("所有数据库表已删除")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    数据库会话上下文管理器。
    
    用法::
    
        with get_db_session() as session:
            task = session.get(TranslationTask, task_id)
    """
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_health() -> dict[str, object]:
    """检查数据库健康状态"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM translation_tasks"))
            task_count = result.scalar()
            result2 = conn.execute(text("SELECT COUNT(*) FROM translation_cache"))
            cache_count = result2.scalar()

        db_path = Path(get_settings().db_path)
        db_size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0

        return {
            "status": "healthy",
            "task_count": task_count,
            "cache_count": cache_count,
            "db_size_mb": round(db_size_mb, 2),
            "db_path": str(db_path),
        }
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {"status": "unhealthy", "error": str(e)}
