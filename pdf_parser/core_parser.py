"""
太玄智译 - PDF核心解析器
基于 PyMuPDF (fitz) 实现高性能PDF解析，pdfminer.six 作为辅助
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger

from taixuan_translator.core.exceptions import (
    PDFCorruptedError,
    PDFEncryptedError,
    PDFParseError,
)
from taixuan_translator.core.utils import timeit


@dataclass
class TextBlock:
    """文本块（段落/标题/正文）"""
    text: str
    page_number: int
    block_type: str = "text"       # text / title / formula / table / image / caption
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)  # (x0, y0, x1, y1)
    font_size: float = 10.0
    font_name: str = ""
    is_bold: bool = False
    is_italic: bool = False
    reading_order: int = 0         # 阅读顺序索引


@dataclass
class PageContent:
    """单页解析结果"""
    page_number: int
    width: float
    height: float
    blocks: list[TextBlock] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)   # 图片元数据
    tables: list[dict] = field(default_factory=list)   # 表格区域

    @property
    def text_blocks(self) -> list[TextBlock]:
        return [b for b in self.blocks if b.block_type not in ("image",)]

    @property
    def plain_text(self) -> str:
        return "\n\n".join(b.text for b in self.text_blocks if b.text.strip())


@dataclass
class DocumentContent:
    """完整文档解析结果"""
    file_path: str
    total_pages: int
    pages: list[PageContent] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    toc: list[dict] = field(default_factory=list)      # 目录结构

    @property
    def all_blocks(self) -> list[TextBlock]:
        blocks = []
        for page in self.pages:
            blocks.extend(page.blocks)
        return blocks

    @property
    def total_chars(self) -> int:
        return sum(len(b.text) for b in self.all_blocks)


class PDFCoreParser:
    """
    PDF核心解析器（PyMuPDF主力 + pdfminer.six辅助）
    
    职责：
    - 打开/验证PDF文件
    - 逐页提取文本块、图片、表格区域
    - 识别标题层级（基于字体大小）
    - 提取文档元数据和目录
    """

    # 标题字体大小阈值（相对于正文字体）
    TITLE_FONT_RATIO = 1.2

    def __init__(self) -> None:
        self._fitz_available = self._check_fitz()

    @staticmethod
    def _check_fitz() -> bool:
        try:
            import fitz  # noqa: F401
            return True
        except ImportError:
            logger.warning("PyMuPDF (fitz) 未安装，将使用 pdfminer.six 降级解析")
            return False

    @timeit
    def parse(self, file_path: str | Path) -> DocumentContent:
        """
        解析PDF文件，返回结构化内容。
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            DocumentContent
            
        Raises:
            PDFEncryptedError: 文件已加密
            PDFCorruptedError: 文件损坏
            PDFParseError: 其他解析错误
        """
        path = Path(file_path)
        if not path.exists():
            raise PDFParseError(f"文件不存在: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise PDFParseError(f"不是PDF文件: {file_path}")

        logger.info(f"开始解析PDF: {path.name}")

        if self._fitz_available:
            return self._parse_with_fitz(path)
        else:
            return self._parse_with_pdfminer(path)

    def _parse_with_fitz(self, path: Path) -> DocumentContent:
        """使用 PyMuPDF 解析（主力方案）"""
        try:
            import fitz  # type: ignore[import]
        except ImportError as e:
            raise PDFParseError("PyMuPDF 未安装") from e

        try:
            doc = fitz.open(str(path))
        except Exception as e:
            raise PDFCorruptedError(str(path)) from e

        # 检查加密
        if doc.is_encrypted:
            doc.close()
            raise PDFEncryptedError(str(path))

        try:
            # 提取元数据
            metadata = dict(doc.metadata) if doc.metadata else {}
            
            # 提取目录
            toc = []
            for level, title, page_num in doc.get_toc():
                toc.append({"level": level, "title": title, "page": page_num})

            # 计算正文基准字体大小
            body_font_size = self._estimate_body_font_size(doc)

            # 逐页解析
            pages = []
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_content = self._parse_page_fitz(
                    page, page_idx + 1, body_font_size
                )
                pages.append(page_content)
                logger.debug(
                    f"  第{page_idx + 1}页: {len(page_content.blocks)}个文本块"
                )

            doc.close()

            content = DocumentContent(
                file_path=str(path),
                total_pages=len(pages),
                pages=pages,
                metadata=metadata,
                toc=toc,
            )
            logger.info(
                f"PDF解析完成: {path.name}, "
                f"{content.total_pages}页, "
                f"{content.total_chars}字符"
            )
            return content

        except (PDFEncryptedError, PDFCorruptedError):
            raise
        except Exception as e:
            raise PDFParseError(f"PDF解析失败: {path.name}", detail=str(e)) from e

    def _parse_page_fitz(
        self,
        page: object,
        page_number: int,
        body_font_size: float,
    ) -> PageContent:
        """解析单页内容（PyMuPDF）"""
        import fitz  # type: ignore[import]

        rect = page.rect  # type: ignore[attr-defined]
        page_content = PageContent(
            page_number=page_number,
            width=rect.width,
            height=rect.height,
        )

        # 提取文本块（带格式信息）
        blocks_raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)  # type: ignore[attr-defined]
        reading_order = 0

        for block in blocks_raw.get("blocks", []):
            block_type = block.get("type", 0)

            if block_type == 0:  # 文本块
                text_block = self._process_text_block(
                    block, page_number, body_font_size, reading_order
                )
                if text_block and text_block.text.strip():
                    page_content.blocks.append(text_block)
                    reading_order += 1

            elif block_type == 1:  # 图片块
                bbox = block.get("bbox", (0, 0, 0, 0))
                page_content.images.append({
                    "page": page_number,
                    "bbox": bbox,
                    "width": bbox[2] - bbox[0],
                    "height": bbox[3] - bbox[1],
                })

        return page_content

    def _process_text_block(
        self,
        block: dict,
        page_number: int,
        body_font_size: float,
        reading_order: int,
    ) -> Optional[TextBlock]:
        """处理单个文本块，提取格式信息"""
        lines = block.get("lines", [])
        if not lines:
            return None

        # 收集所有span的文本和字体信息
        full_text_parts = []
        max_font_size = 0.0
        font_name = ""
        is_bold = False
        is_italic = False

        for line in lines:
            for span in line.get("spans", []):
                span_text = span.get("text", "").strip()
                if span_text:
                    full_text_parts.append(span_text)
                    span_size = span.get("size", 10.0)
                    if span_size > max_font_size:
                        max_font_size = span_size
                        font_name = span.get("font", "")
                    flags = span.get("flags", 0)
                    if flags & 2**4:  # bold
                        is_bold = True
                    if flags & 2**1:  # italic
                        is_italic = True

        full_text = " ".join(full_text_parts)
        if not full_text.strip():
            return None

        # 判断是否为标题
        block_type = "text"
        if max_font_size >= body_font_size * self.TITLE_FONT_RATIO or is_bold:
            block_type = "title"

        bbox = block.get("bbox", (0, 0, 0, 0))

        return TextBlock(
            text=full_text,
            page_number=page_number,
            block_type=block_type,
            bbox=tuple(bbox),  # type: ignore[arg-type]
            font_size=max_font_size,
            font_name=font_name,
            is_bold=is_bold,
            is_italic=is_italic,
            reading_order=reading_order,
        )

    def _estimate_body_font_size(self, doc: object) -> float:
        """
        估算文档正文字体大小（取前5页字体大小的众数）。
        """
        from collections import Counter
        font_sizes: list[float] = []

        sample_pages = min(5, len(doc))  # type: ignore[arg-type]
        for i in range(sample_pages):
            page = doc[i]  # type: ignore[index]
            blocks = page.get_text("dict").get("blocks", [])  # type: ignore[attr-defined]
            for block in blocks:
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            size = round(span.get("size", 0), 1)
                            if 6 <= size <= 20:  # 过滤异常值
                                font_sizes.append(size)

        if not font_sizes:
            return 10.0

        counter = Counter(font_sizes)
        return counter.most_common(1)[0][0]

    def _parse_with_pdfminer(self, path: Path) -> DocumentContent:
        """使用 pdfminer.six 解析（降级方案）"""
        try:
            from pdfminer.high_level import extract_pages  # type: ignore[import]
            from pdfminer.layout import LTTextBox, LTFigure  # type: ignore[import]
        except ImportError as e:
            raise PDFParseError("pdfminer.six 未安装，请安装: pip install pdfminer.six") from e

        pages = []
        try:
            for page_idx, page_layout in enumerate(extract_pages(str(path))):
                page_content = PageContent(
                    page_number=page_idx + 1,
                    width=page_layout.width,
                    height=page_layout.height,
                )
                reading_order = 0
                for element in page_layout:
                    if isinstance(element, LTTextBox):
                        text = element.get_text().strip()
                        if text:
                            page_content.blocks.append(TextBlock(
                                text=text,
                                page_number=page_idx + 1,
                                bbox=(
                                    element.x0, element.y0,
                                    element.x1, element.y1
                                ),
                                reading_order=reading_order,
                            ))
                            reading_order += 1
                    elif isinstance(element, LTFigure):
                        page_content.images.append({
                            "page": page_idx + 1,
                            "bbox": (element.x0, element.y0, element.x1, element.y1),
                        })
                pages.append(page_content)

        except Exception as e:
            raise PDFParseError(f"pdfminer解析失败: {path.name}", detail=str(e)) from e

        return DocumentContent(
            file_path=str(path),
            total_pages=len(pages),
            pages=pages,
        )
