"""
测试：API Schemas 数据模型
"""
import pytest
from taixuan_translator.api.schemas import (
    ApiResponse,
    ParsedSegment,
    UploadResponse,
    TaskStatusResponse,
    ExportDocxRequest,
    ExportSegment,
    TranslateRequest,
    SegmentType,
    TaskStatusEnum,
    BilingualModeEnum,
)


def test_api_response_ok():
    """测试成功响应"""
    resp = ApiResponse.ok(data={"key": "value"}, message="操作成功")
    assert resp.success is True
    assert resp.code == 200
    assert resp.data == {"key": "value"}


def test_api_response_error():
    """测试错误响应"""
    resp = ApiResponse.error("文件过大", code=413)
    assert resp.success is False
    assert resp.code == 413
    assert resp.message == "文件过大"


def test_parsed_segment():
    """测试段落数据模型"""
    seg = ParsedSegment(
        index=0,
        page=1,
        type=SegmentType.TEXT,
        text="Hello World",
        font_size=10.5,
        is_bold=False,
    )
    assert seg.index == 0
    assert seg.type == SegmentType.TEXT
    assert "Hello" in seg.text


def test_upload_response():
    """测试上传响应"""
    resp = UploadResponse(
        task_id=42,
        file_name="paper.pdf",
        file_type="pdf",
        total_pages=10,
        total_segments=156,
        segments=[],
        parse_duration_ms=2341,
    )
    assert resp.task_id == 42
    assert resp.total_segments == 156
    assert resp.parse_duration_ms == 2341


def test_export_request():
    """测试导出请求"""
    req = ExportDocxRequest(
        file_name="paper.pdf",
        segments=[
            ExportSegment(index=0, source_text="Hi", translated_text="你好", page=1),
            ExportSegment(index=1, source_text="Hello", translated_text="你好", page=1),
        ],
        bilingual_mode=BilingualModeEnum.INTERLEAVED,
        target_language="zh-Hans",
    )
    assert len(req.segments) == 2
    assert req.bilingual_mode == BilingualModeEnum.INTERLEAVED


def test_task_status_response():
    """测试任务状态响应"""
    resp = TaskStatusResponse(
        task_id=42,
        status=TaskStatusEnum.TRANSLATING,
        progress=45,
        current_step="正在翻译第23/52段...",
        total_segments=52,
        translated_segments=23,
    )
    assert resp.progress == 45
    assert resp.status == TaskStatusEnum.TRANSLATING
    assert not resp.error_message


def test_translate_request():
    """测试翻译请求"""
    req = TranslateRequest(
        task_id=42,
        segments=[{"index": 0, "text": "Hello"}, {"index": 1, "text": "World"}],
        engine="openai",
        target_language="zh-Hans",
    )
    assert len(req.segments) == 2
    assert req.engine == "openai"
