"""
太玄智译 - SQLAlchemy ORM 数据模型
涵盖：翻译任务、翻译历史、翻译缓存、用户配置
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """所有模型的基类"""
    pass


# ─── 枚举类型 ────────────────────────────────────────────────────────────────

class TaskStatus(str, enum.Enum):
    PENDING = "pending"       # 等待中
    RUNNING = "running"       # 翻译中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消
    PAUSED = "paused"         # 已暂停


class EngineType(str, enum.Enum):
    OPENAI = "openai"
    DEEPL = "deepl"
    OLLAMA = "ollama"


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    EPUB = "epub"
    HTML = "html"
    TXT = "txt"
    SRT = "srt"
    ASS = "ass"


# ─── 翻译任务表 ──────────────────────────────────────────────────────────────

class TranslationTask(Base):
    """翻译任务主表"""
    __tablename__ = "translation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 文件信息
    source_file_path: Mapped[str] = mapped_column(String(1024), nullable=False, comment="源文件路径")
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="源文件名")
    source_file_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="源文件MD5")
    source_file_size: Mapped[int] = mapped_column(Integer, default=0, comment="源文件大小（字节）")
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), nullable=False, comment="文档类型"
    )
    
    # 翻译配置
    engine: Mapped[EngineType] = mapped_column(
        Enum(EngineType), nullable=False, comment="翻译引擎"
    )
    source_language: Mapped[str] = mapped_column(String(20), default="auto", comment="源语言")
    target_language: Mapped[str] = mapped_column(String(20), nullable=False, comment="目标语言")
    bilingual_mode: Mapped[str] = mapped_column(String(30), default="interleaved", comment="双语模式")
    
    # 任务状态
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, comment="任务状态"
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="进度百分比 0-100")
    total_pages: Mapped[int] = mapped_column(Integer, default=0, comment="总页数")
    processed_pages: Mapped[int] = mapped_column(Integer, default=0, comment="已处理页数")
    total_segments: Mapped[int] = mapped_column(Integer, default=0, comment="总段落数")
    translated_segments: Mapped[int] = mapped_column(Integer, default=0, comment="已翻译段落数")
    total_chars: Mapped[int] = mapped_column(Integer, default=0, comment="总字符数")
    translated_chars: Mapped[int] = mapped_column(Integer, default=0, comment="已翻译字符数")
    
    # 输出信息
    output_file_path: Mapped[Optional[str]] = mapped_column(String(1024), comment="输出文件路径")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    
    # 统计信息
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, comment="翻译耗时（秒）")
    api_tokens_used: Mapped[int] = mapped_column(Integer, default=0, comment="消耗的API Token数")
    cache_hit_count: Mapped[int] = mapped_column(Integer, default=0, comment="缓存命中次数")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, comment="创建时间"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="完成时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # 关联
    segments: Mapped[list["TranslationSegment"]] = relationship(
        "TranslationSegment", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_created_at", "created_at"),
        Index("ix_tasks_file_hash", "source_file_hash"),
    )

    def __repr__(self) -> str:
        return f"<TranslationTask id={self.id} file={self.source_file_name} status={self.status}>"


# ─── 翻译段落表 ──────────────────────────────────────────────────────────────

class TranslationSegment(Base):
    """翻译段落记录（每个文本块的翻译结果）"""
    __tablename__ = "translation_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("translation_tasks.id", ondelete="CASCADE"), nullable=False
    )
    
    # 段落信息
    page_number: Mapped[int] = mapped_column(Integer, default=0, comment="所在页码")
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="段落序号")
    segment_type: Mapped[str] = mapped_column(
        String(30), default="text", comment="段落类型: text/formula/table/image/title"
    )
    
    # 内容
    source_text: Mapped[str] = mapped_column(Text, nullable=False, comment="原文")
    translated_text: Mapped[Optional[str]] = mapped_column(Text, comment="译文")
    
    # 状态
    is_translated: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已翻译")
    is_cached: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否来自缓存")
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否被用户编辑")
    
    # 质量
    confidence: Mapped[Optional[float]] = mapped_column(Float, comment="翻译置信度 0-1")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # 关联
    task: Mapped["TranslationTask"] = relationship("TranslationTask", back_populates="segments")

    __table_args__ = (
        Index("ix_segments_task_id", "task_id"),
        Index("ix_segments_task_page", "task_id", "page_number"),
    )

    def __repr__(self) -> str:
        return f"<TranslationSegment task={self.task_id} page={self.page_number} idx={self.segment_index}>"


# ─── 翻译缓存表 ──────────────────────────────────────────────────────────────

class TranslationCache(Base):
    """翻译缓存表（避免重复翻译相同内容）"""
    __tablename__ = "translation_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 缓存键（source_hash + engine + source_lang + target_lang）
    cache_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="缓存键")
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="原文MD5")
    
    # 内容
    source_text: Mapped[str] = mapped_column(Text, nullable=False, comment="原文")
    translated_text: Mapped[str] = mapped_column(Text, nullable=False, comment="译文")
    
    # 元数据
    engine: Mapped[str] = mapped_column(String(30), nullable=False, comment="翻译引擎")
    source_language: Mapped[str] = mapped_column(String(20), nullable=False, comment="源语言")
    target_language: Mapped[str] = mapped_column(String(20), nullable=False, comment="目标语言")
    model_name: Mapped[Optional[str]] = mapped_column(String(100), comment="使用的模型名称")
    
    # 统计
    hit_count: Mapped[int] = mapped_column(Integer, default=0, comment="命中次数")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="过期时间")

    __table_args__ = (
        Index("ix_cache_key", "cache_key"),
        Index("ix_cache_source_hash", "source_hash"),
        Index("ix_cache_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<TranslationCache engine={self.engine} hits={self.hit_count}>"


# ─── 用户配置表 ──────────────────────────────────────────────────────────────

class UserPreference(Base):
    """用户偏好配置（KV存储）"""
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="配置键")
    value: Mapped[str] = mapped_column(Text, nullable=False, comment="配置值（JSON序列化）")
    description: Mapped[Optional[str]] = mapped_column(String(255), comment="配置说明")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("key", name="uq_preference_key"),
    )

    def __repr__(self) -> str:
        return f"<UserPreference key={self.key}>"
