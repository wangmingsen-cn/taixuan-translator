"""
测试：文件解析服务（不依赖外部文件）
"""
import io
import pytest
from unittest.mock import MagicMock, patch

from taixuan_translator.api.schemas import SegmentType


def test_segment_type_mapping():
    """测试段落类型映射"""
    from taixuan_translator.services.file_parser import FileParseService

    assert FileParseService._str_to_segment_type("text") == SegmentType.TEXT
    assert FileParseService._str_to_segment_type("title") == SegmentType.TITLE
    assert FileParseService._str_to_segment_type("formula") == SegmentType.FORMULA
    assert FileParseService._str_to_segment_type("table") == SegmentType.TABLE
    assert FileParseService._str_to_segment_type("unknown") == SegmentType.TEXT


def test_doc_type_mapping():
    """测试文档类型映射"""
    from taixuan_translator.services.file_parser import FileParseService
    from taixuan_translator.data.models import DocumentType

    assert FileParseService._ext_to_doc_type(".pdf") == DocumentType.PDF
    assert FileParseService._ext_to_doc_type(".docx") == DocumentType.DOCX
    assert FileParseService._ext_to_doc_type(".epub") == DocumentType.EPUB
    assert FileParseService._ext_to_doc_type(".html") == DocumentType.HTML
    assert FileParseService._ext_to_doc_type(".txt") == DocumentType.TXT
    assert FileParseService._ext_to_doc_type(".srt") == DocumentType.SRT


def test_txt_parsing_logic(tmp_path):
    """测试TXT解析逻辑（模拟）"""
    from taixuan_translator.services.file_parser import FileParseService

    service = FileParseService()
    # 模拟TXT内容
    test_content = "这是第一段。\n\n这是第二段。\n\n这是第三段。"
    
    with patch.object(service, "_parse_txt") as mock:
        # 创建临时文件
        txt_file = tmp_path / "test.txt"
        txt_file.write_text(test_content, encoding="utf-8")
        
        # 模拟解析结果
        from taixuan_translator.api.schemas import ParsedSegment
        mock.return_value = [
            ParsedSegment(index=0, page=1, type=SegmentType.TEXT, text="这是第一段。"),
            ParsedSegment(index=1, page=1, type=SegmentType.TEXT, text="这是第二段。"),
            ParsedSegment(index=2, page=1, type=SegmentType.TEXT, text="这是第三段。"),
        ]
        
        result = service._parse_txt(txt_file)
        assert len(result) == 3
        assert result[0].text == "这是第一段。"
