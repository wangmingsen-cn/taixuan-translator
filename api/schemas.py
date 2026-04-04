"""
太玄智译 - API 数据模型（Request / Response Schemas）
所有接口的入参和出参均在此定义，前后端契约文档
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── 通用响应包装 ────────────────────────────────────────────────────────────

class ApiResponse(BaseModel):
    """统一响应格式"""
    success: bool = True
    code: int = 200
    message: str = "ok"
    data: Optional[Any] = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "ok") -> "ApiResponse":
        return cls(success=True, code=200, message=message, data=data)

    @classmethod
    def error(cls, message: str, code: int = 400) -> "ApiResponse":
        return cls(success=False, code=code, message=message, data=None)


# ─── 文件上传 /api/upload ────────────────────────────────────────────────────

class SegmentType(str, Enum):
    TEXT = "text"
    TITLE = "title"
    FORMULA = "formula"
    TABLE = "table"
    IMAGE = "image"
    CAPTION = "caption"


class ParsedSegment(BaseModel):
    """解析后的文本段落（返回给前端）"""
    index: int = Field(..., description="段落序号（全局唯一，用于翻译结果回填）")
    page: int = Field(default=1, description="所在页码")
    type: SegmentType = Field(default=SegmentType.TEXT, description="段落类型")
    text: str = Field(..., description="原文内容")
    bbox: Optional[list[float]] = Field(default=None, description="位置坐标 [x0,y0,x1,y1]")
    font_size: Optional[float] = Field(default=None, description="字体大小（pt）")
    is_bold: bool = Field(default=False, description="是否粗体")


class UploadResponse(BaseModel):
    """POST /api/upload 响应"""
    task_id: int = Field(..., description="任务ID，用于查询进度")
    file_name: str = Field(..., description="原始文件名")
    file_type: str = Field(..., description="文件类型：pdf/docx/epub/html/txt/srt")
    total_pages: int = Field(default=0, description="总页数（PDF/DOCX）")
    total_segments: int = Field(..., description="解析出的段落总数")
    segments: list[ParsedSegment] = Field(default_factory=list, description="段落列表")
    parse_duration_ms: int = Field(default=0, description="解析耗时（毫秒）")
    warnings: list[str] = Field(default_factory=list, description="解析警告信息")


# ─── 任务状态 /api/status/:taskId ────────────────────────────────────────────

class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    TRANSLATING = "translating"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskStatusResponse(BaseModel):
    """GET /api/status/:taskId 响应"""
    task_id: int
    status: TaskStatusEnum
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比")
    current_step: str = Field(default="", description="当前步骤描述")
    total_segments: int = Field(default=0)
    translated_segments: int = Field(default=0)
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None


# ─── 导出 /api/export/docx ───────────────────────────────────────────────────

class BilingualModeEnum(str, Enum):
    INTERLEAVED = "interleaved"    # 段落交替（原文灰色 + 译文黑色）
    SIDE_BY_SIDE = "side_by_side"  # 左右分栏
    TRANSLATED_ONLY = "translated_only"  # 仅译文
    FOOTNOTE = "footnote"          # 脚注模式


class ExportSegment(BaseModel):
    """导出时前端回传的翻译结果"""
    index: int = Field(..., description="段落序号（与上传时一致）")
    source_text: str = Field(..., description="原文")
    translated_text: str = Field(..., description="译文")
    type: SegmentType = Field(default=SegmentType.TEXT)
    page: int = Field(default=1)


class ExportDocxRequest(BaseModel):
    """POST /api/export/docx 请求体"""
    task_id: Optional[int] = Field(default=None, description="关联任务ID（可选）")
    file_name: str = Field(..., description="原始文件名（用于生成输出文件名）")
    segments: list[ExportSegment] = Field(..., description="翻译后的段落列表")
    bilingual_mode: BilingualModeEnum = Field(
        default=BilingualModeEnum.INTERLEAVED,
        description="双语模式"
    )
    source_language: str = Field(default="en", description="源语言")
    target_language: str = Field(default="zh-Hans", description="目标语言")
    include_toc: bool = Field(default=True, description="是否生成目录")
    apply_publication_std: bool = Field(
        default=True, description="是否应用GB/T 7713.1-2006出版标准"
    )


class ExportDocxResponse(BaseModel):
    """POST /api/export/docx 响应"""
    download_url: str = Field(..., description="Word文件下载URL")
    file_name: str = Field(..., description="生成的文件名")
    file_size_kb: int = Field(default=0, description="文件大小（KB）")
    total_segments: int = Field(default=0, description="导出段落数")
    expires_in_seconds: int = Field(default=3600, description="下载链接有效期（秒）")


# ─── 翻译接口 /api/translate ─────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    """POST /api/translate 请求体（单段/批量翻译）"""
    task_id: Optional[int] = Field(default=None, description="关联任务ID")
    segments: list[dict] = Field(..., description="待翻译段落列表 [{index, text}]")
    engine: str = Field(default="openai", description="翻译引擎: openai/deepl/ollama/deepseek")
    source_language: str = Field(default="auto")
    target_language: str = Field(default="zh-Hans")


class TranslateResponse(BaseModel):
    """POST /api/translate 响应"""
    task_id: Optional[int] = None
    results: list[dict] = Field(default_factory=list, description="[{index, source, translated, from_cache}]")
    total_tokens: int = Field(default=0)
    cache_hits: int = Field(default=0)
    duration_ms: int = Field(default=0)
