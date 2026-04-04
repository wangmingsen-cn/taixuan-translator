"""
太玄智译 - 文档导出服务层
负责生成出版级 Word / TXT 文件
"""
from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path
from typing import Optional

from loguru import logger

from taixuan_translator.api.schemas import (
    BilingualModeEnum,
    ExportDocxRequest,
    ExportDocxResponse,
    ExportSegment,
)
from taixuan_translator.core.config import BilingualMode, get_settings
from taixuan_translator.core.exceptions import DocxGenerationError
from taixuan_translator.core.utils import safe_filename
from taixuan_translator.pdf_parser.core_parser import DocumentContent, PageContent, TextBlock


class ExportService:
    """
    文档导出服务
    
    支持格式：
    - Word (.docx) — 出版级 GB/T 7713.1-2006 标准
    - TXT — 纯译文 / 双语对照
    - 双语 HTML — 浏览器直接打开
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def export_docx(self, request: ExportDocxRequest) -> ExportDocxResponse:
        """
        导出 Word 文档。
        
        Args:
            request: 导出请求（含翻译后的段落列表）
            
        Returns:
            ExportDocxResponse（含下载链接）
        """
        logger.info(f"[ExportService] 导出Word: {request.file_name}, {len(request.segments)}段落")
        start = time.time()

        # 构建翻译字典 {index: translated_text}
        translations: dict[int, str] = {}
        for seg in request.segments:
            translations[seg.index] = seg.translated_text

        # 构造 DocumentContent（虚构，用于Word生成器）
        pages: list[PageContent] = []
        page_map: dict[int, list[ExportSegment]] = {}

        for seg in request.segments:
            if seg.page not in page_map:
                page_map[seg.page] = []
            page_map[seg.page].append(seg)

        for page_num in sorted(page_map.keys()):
            segs = page_map[page_num]
            blocks = []
            for i, seg in enumerate(segs):
                blocks.append(TextBlock(
                    text=seg.source_text,
                    page_number=seg.page,
                    block_type=seg.type.value,
                    reading_order=seg.index,
                ))
            pages.append(PageContent(
                page_number=page_num,
                width=595.0,
                height=842.0,
                blocks=blocks,
            ))

        doc_content = DocumentContent(
            file_path=request.file_name,
            total_pages=max(p.page_number for p in pages) if pages else 1,
            pages=pages,
        )

        # 生成输出文件名
        base_name = Path(request.file_name).stem
        output_name = safe_filename(f"{base_name}_翻译") + ".docx"
        output_dir = self.settings.app_dir / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_name

        # 调用 Word 生成器
        bilingual_mode_map = {
            BilingualModeEnum.INTERLEAVED: BilingualMode.INTERLEAVED,
            BilingualModeEnum.SIDE_BY_SIDE: BilingualMode.SIDE_BY_SIDE,
            BilingualModeEnum.TRANSLATED_ONLY: BilingualMode.INTERLEAVED,
            BilingualModeEnum.FOOTNOTE: BilingualMode.FOOTNOTE,
        }
        mode = bilingual_mode_map.get(request.bilingual_mode, BilingualMode.INTERLEAVED)

        from taixuan_translator.docx_generator.core import DocxGenerator
        gen = DocxGenerator()
        gen.generate(
            document=doc_content,
            translations=translations,
            output_path=output_path,
            bilingual_mode=mode,
            translated_only=(request.bilingual_mode == BilingualModeEnum.TRANSLATED_ONLY),
        )

        file_size_kb = int(output_path.stat().st_size / 1024)
        elapsed = time.time() - start
        logger.info(f"[ExportService] Word导出完成: {output_path.name}, {file_size_kb}KB, {elapsed:.1f}s")

        # 生成访问URL（相对路径，供前端下载）
        download_url = f"/api/downloads/{output_name}"

        return ExportDocxResponse(
            download_url=download_url,
            file_name=output_name,
            file_size_kb=file_size_kb,
            total_segments=len(request.segments),
            expires_in_seconds=3600,
        )

    def export_txt(
        self,
        segments: list[ExportSegment],
        bilingual: bool = False,
    ) -> bytes:
        """
        导出纯文本。
        
        Args:
            segments: 翻译后的段落列表
            bilingual: 是否包含双语对照
            
        Returns:
            UTF-8 编码的字节流
        """
        lines: list[str] = []
        for seg in segments:
            if bilingual:
                lines.append(f"【原文】{seg.source_text}")
                lines.append(f"【译文】{seg.translated_text}")
                lines.append("")
            else:
                lines.append(seg.translated_text)

        content = "\n".join(lines)
        return content.encode("utf-8-sig")  # BOM for Excel 兼容性

    def export_html_bilingual(
        self,
        file_name: str,
        segments: list[ExportSegment],
    ) -> bytes:
        """
        导出双语对照 HTML（浏览器直接打开，可打印为PDF）。
        
        Returns:
            HTML 字节流
        """
        rows_html = ""
        for seg in segments:
            rows_html += f"""
            <tr>
                <td class="src">{seg.source_text}</td>
                <td class="trans">{seg.translated_text}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{file_name} - 双语对照</title>
<style>
  body {{ font-family: '微软雅黑', Arial, sans-serif; font-size: 14px; margin: 40px; }}
  h1 {{ border-bottom: 2px solid #1890ff; padding-bottom: 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
  td {{ border: 1px solid #ddd; padding: 12px; vertical-align: top; }}
  td.src {{ width: 50%; color: #666; background: #fafafa; }}
  td.trans {{ width: 50%; }}
  tr:hover td {{ background: #f0f7ff; }}
</style>
</head>
<body>
<h1>{file_name}</h1>
<table>
  <thead><tr><th>原文</th><th>译文</th></tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</body>
</html>"""
        return html.encode("utf-8")
