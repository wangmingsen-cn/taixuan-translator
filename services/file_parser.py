"""
太玄智译 - 文件解析服务层
统一入口：根据文件类型分发到不同解析器
"""
from __future__ import annotations

import io
import time
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

from taixuan_translator.api.schemas import ParsedSegment, SegmentType, UploadResponse
from taixuan_translator.core.exceptions import (
    FileOperationError,
    FileTooLargeError,
    PDFParseError,
    UnsupportedFileTypeError,
)
from taixuan_translator.core.utils import get_file_size_mb, is_supported_file, compute_file_hash
from taixuan_translator.data.database import get_db_session
from taixuan_translator.data.models import DocumentType, EngineType, TaskStatus, TranslationTask


MAX_FILE_SIZE_MB = 500
SUPPORTED_TYPES = {".pdf", ".docx", ".doc", ".epub", ".html", ".htm", ".txt", ".srt", ".ass"}


class FileParseService:
    """
    文件解析服务（统一调度层）
    
    职责：
    1. 接收上传文件流，保存到临时目录
    2. 校验文件类型和大小
    3. 根据扩展名分发到对应解析器
    4. 持久化任务记录
    5. 返回结构化段落数据
    """

    def __init__(self) -> None:
        self._parsers: dict[str, object] = {}

    # ─── 公共接口 ──────────────────────────────────────────────────────────────

    def parse_upload(
        self,
        file_stream: io.BytesIO,
        file_name: str,
        file_size: int,
    ) -> UploadResponse:
        """
        解析上传文件，返回段落列表。
        
        Args:
            file_stream: 文件二进制流
            file_name: 文件名（含扩展名）
            file_size: 文件大小（字节）
            
        Returns:
            UploadResponse（含 task_id + 段落列表）
        """
        start_time = time.time()
        path = Path(file_name)
        ext = path.suffix.lower()

        # 1. 校验
        if ext not in SUPPORTED_TYPES:
            raise UnsupportedFileTypeError(
                file_name,
                list(SUPPORTED_TYPES)
            )

        size_mb = file_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise FileTooLargeError(file_name, size_mb, MAX_FILE_SIZE_MB)

        logger.info(f"[ParseService] 解析文件: {file_name} ({size_mb:.1f}MB)")

        # 2. 保存到临时文件
        temp_path = self._save_temp(file_stream, file_name)

        try:
            # 3. 分发解析
            if ext == ".pdf":
                result = self._parse_pdf(temp_path)
            elif ext in (".docx", ".doc"):
                result = self._parse_docx(temp_path)
            elif ext == ".epub":
                result = self._parse_epub(temp_path)
            elif ext in (".html", ".htm"):
                result = self._parse_html(temp_path)
            elif ext == ".txt":
                result = self._parse_txt(temp_path)
            elif ext in (".srt", ".ass"):
                result = self._parse_subtitle(temp_path, ext)
            else:
                raise UnsupportedFileTypeError(file_name)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 4. 持久化任务
            task_id = self._create_task(
                file_path=str(temp_path),
                file_name=file_name,
                file_size=file_size,
                doc_type=self._ext_to_doc_type(ext),
                total_segments=len(result),
            )

            logger.info(
                f"[ParseService] 解析完成: {file_name}, "
                f"{len(result)}段落, {elapsed_ms}ms"
            )

            return UploadResponse(
                task_id=task_id,
                file_name=file_name,
                file_type=ext.lstrip("."),
                total_pages=getattr(result[0], "page", 1) if result else 0,
                total_segments=len(result),
                segments=result,
                parse_duration_ms=elapsed_ms,
                warnings=[],
            )

        except Exception:
            raise
        finally:
            # 不删除临时文件，保留给后续翻译流程使用
            pass

    # ─── 各格式解析器 ─────────────────────────────────────────────────────────

    def _parse_pdf(self, file_path: Path) -> list[ParsedSegment]:
        """解析 PDF"""
        try:
            from taixuan_translator.pdf_parser.core_parser import PDFCoreParser

            parser = PDFCoreParser()
            doc = parser.parse(file_path)

            segments = []
            idx = 0
            for page in doc.pages:
                for block in page.text_blocks:
                    segments.append(ParsedSegment(
                        index=idx,
                        page=page.page_number,
                        type=self._str_to_segment_type(block.block_type),
                        text=block.text,
                        bbox=list(block.bbox) if block.bbox else None,
                        font_size=block.font_size or None,
                        is_bold=block.is_bold,
                    ))
                    idx += 1

            return segments

        except PDFParseError:
            raise
        except Exception as e:
            raise PDFParseError(f"PDF解析失败: {file_path.name}", detail=str(e)) from e

    def _parse_docx(self, file_path: Path) -> list[ParsedSegment]:
        """解析 Word 文档"""
        try:
            from docx import Document  # type: ignore[import]

            doc = Document(str(file_path))
            segments = []
            idx = 0

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue

                # 判断段落样式
                seg_type = SegmentType.TEXT
                if para.style and para.style.name.startswith("Heading"):
                    seg_type = SegmentType.TITLE
                elif any(run.bold for run in para.runs if run.text.strip()):
                    seg_type = SegmentType.TITLE

                segments.append(ParsedSegment(
                    index=idx,
                    page=1,
                    type=seg_type,
                    text=text,
                ))
                idx += 1

            return segments

        except Exception as e:
            raise FileOperationError(f"Word文档解析失败: {file_path.name}", detail=str(e)) from e

    def _parse_epub(self, file_path: Path) -> list[ParsedSegment]:
        """解析 ePub 电子书"""
        try:
            import ebooklib  # type: ignore[import]
            from ebooklib.epub import epub_book_read  # type: ignore[import]
        except ImportError:
            raise FileOperationError(
                "ePub解析需要安装 ebooklib: pip install ebooklib"
            )

        segments = []
        idx = 0

        try:
            book = epub_book_read(str(file_path))  # type: ignore[attr-defined]

            for item in book.items:  # type: ignore[attr-defined]
                if item.get_type() == 896:  # HTML
                    content = item.get_content().decode("utf-8", errors="ignore")
                    texts = self._extract_html_text(content)
                    for text in texts:
                        if text.strip():
                            segments.append(ParsedSegment(
                                index=idx,
                                page=1,
                                type=SegmentType.TEXT,
                                text=text,
                            ))
                            idx += 1

        except Exception as e:
            logger.warning(f"ePub解析部分失败: {e}")

        return segments

    def _parse_html(self, file_path: Path) -> list[ParsedSegment]:
        """解析 HTML 网页"""
        try:
            from bs4 import BeautifulSoup  # type: ignore[import]
        except ImportError:
            raise FileOperationError("BeautifulSoup 未安装: pip install beautifulsoup4")

        segments = []
        idx = 0

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "lxml")

        # 移除脚本和样式
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        # 提取正文
        texts = self._extract_html_text(str(soup))
        for text in texts:
            if text.strip():
                segments.append(ParsedSegment(
                    index=idx,
                    page=1,
                    type=SegmentType.TEXT,
                    text=text,
                ))
                idx += 1

        return segments

    def _parse_txt(self, file_path: Path) -> list[ParsedSegment]:
        """解析纯文本"""
        segments = []
        idx = 0

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for para in f.read().split("\n\n"):
                para = para.strip()
                if para:
                    segments.append(ParsedSegment(
                        index=idx,
                        page=1,
                        type=SegmentType.TEXT,
                        text=para,
                    ))
                    idx += 1

        return segments

    def _parse_subtitle(self, file_path: Path, ext: str) -> list[ParsedSegment]:
        """解析 SRT / ASS 字幕"""
        try:
            import pysubs2  # type: ignore[import]
        except ImportError:
            raise FileOperationError("pysubs2 未安装: pip install pysubs2")

        segments = []
        idx = 0

        try:
            subs = pysubs2.load(str(file_path))  # type: ignore[call-arg]
            for line in subs:  # type: ignore[iterable]
                text = line.text.strip() if hasattr(line, "text") else str(line).strip()
                if text and text not in ("", "..."):
                    segments.append(ParsedSegment(
                        index=idx,
                        page=1,
                        type=SegmentType.TEXT,
                        text=text,
                    ))
                    idx += 1
        except Exception as e:
            logger.warning(f"字幕解析失败: {e}")

        return segments

    # ─── 工具方法 ──────────────────────────────────────────────────────────────

    def _save_temp(self, file_stream: io.BytesIO, file_name: str) -> Path:
        """保存上传文件到临时目录"""
        import tempfile
        from taixuan_translator.core.config import get_settings
        settings = get_settings()
        temp_dir = settings.temp_dir
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = f"{int(time.time() * 1000)}_{Path(file_name).name}"
        temp_path = temp_dir / safe_name
        
        file_stream.seek(0)
        with open(temp_path, "wb") as f:
            f.write(file_stream.read())
        
        return temp_path

    def _create_task(
        self,
        file_path: str,
        file_name: str,
        file_size: int,
        doc_type: DocumentType,
        total_segments: int,
    ) -> int:
        """创建数据库任务记录，返回 task_id"""
        file_hash = compute_file_hash(file_path)

        with get_db_session() as session:
            task = TranslationTask(
                source_file_path=file_path,
                source_file_name=file_name,
                source_file_hash=file_hash,
                source_file_size=file_size,
                document_type=doc_type,
                engine=EngineType.OPENAI,
                target_language="zh-Hans",
                total_chars=0,
                total_segments=total_segments,
                status=TaskStatus.PENDING,
            )
            session.add(task)
            session.flush()
            return task.id

    @staticmethod
    def _ext_to_doc_type(ext: str) -> DocumentType:
        mapping = {
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".doc": DocumentType.DOCX,
            ".epub": DocumentType.EPUB,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".txt": DocumentType.TXT,
            ".srt": DocumentType.SRT,
            ".ass": DocumentType.ASS,
        }
        return mapping.get(ext, DocumentType.TXT)

    @staticmethod
    def _str_to_segment_type(s: str) -> SegmentType:
        mapping = {
            "text": SegmentType.TEXT,
            "title": SegmentType.TITLE,
            "formula": SegmentType.FORMULA,
            "table": SegmentType.TABLE,
            "image": SegmentType.IMAGE,
            "caption": SegmentType.CAPTION,
        }
        return mapping.get(s, SegmentType.TEXT)

    @staticmethod
    def _extract_html_text(html: str) -> list[str]:
        """从HTML中提取纯文本段落"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return [html]
        soup = BeautifulSoup(html, "lxml")
        texts = []
        for tag in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "li"]):
            text = tag.get_text(strip=True)
            if text:
                texts.append(text)
        return texts or [soup.get_text(strip=True)]
