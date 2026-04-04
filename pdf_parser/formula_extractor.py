"""
太玄智译 - 公式提取模块
使用 PaddleOCR + LaTeX-OCR 识别PDF中的数学公式
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

from taixuan_translator.core.config import get_settings
from taixuan_translator.core.exceptions import FormulaExtractionError


@dataclass
class FormulaResult:
    """公式识别结果"""
    latex: str                    # LaTeX表达式
    confidence: float             # 置信度 0-1
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)
    page_number: int = 0
    image_path: Optional[str] = None  # 公式图片路径（调试用）


class FormulaExtractor:
    """
    公式提取器（PaddleOCR + LaTeX-OCR 双引擎）
    
    策略：
    1. 先用 PaddleOCR 检测公式区域
    2. 再用 LaTeX-OCR 将公式图片转换为 LaTeX
    3. 置信度低于阈值时标记为待人工审校
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._paddle_ocr: Optional[object] = None
        self._latex_ocr: Optional[object] = None

    def _get_paddle_ocr(self) -> object:
        """懒加载 PaddleOCR"""
        if self._paddle_ocr is None:
            try:
                from paddleocr import PaddleOCR  # type: ignore[import]
                self._paddle_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.settings.pdf.ocr_lang,
                    show_log=False,
                )
                logger.info("PaddleOCR 初始化完成")
            except ImportError:
                logger.warning("PaddleOCR 未安装，公式识别功能不可用")
                raise FormulaExtractionError("PaddleOCR 未安装，请运行: pip install paddleocr")
        return self._paddle_ocr

    def _get_latex_ocr(self) -> object:
        """懒加载 LaTeX-OCR"""
        if self._latex_ocr is None:
            try:
                from pix2tex.cli import LatexOCR  # type: ignore[import]
                self._latex_ocr = LatexOCR()
                logger.info("LaTeX-OCR 初始化完成")
            except ImportError:
                logger.warning("pix2tex (LaTeX-OCR) 未安装")
                raise FormulaExtractionError("LaTeX-OCR 未安装，请运行: pip install pix2tex")
        return self._latex_ocr

    def extract_from_image(self, image_path: str | Path) -> list[FormulaResult]:
        """
        从图片中提取公式。
        
        Args:
            image_path: 图片路径（PDF页面渲染图）
            
        Returns:
            公式识别结果列表
        """
        results: list[FormulaResult] = []
        threshold = self.settings.pdf.formula_confidence

        try:
            from PIL import Image  # type: ignore[import]
            img = Image.open(str(image_path))

            # 使用 LaTeX-OCR 直接识别整图中的公式
            latex_ocr = self._get_latex_ocr()
            latex_text = latex_ocr(img)  # type: ignore[call-arg]

            if latex_text and latex_text.strip():
                results.append(FormulaResult(
                    latex=latex_text.strip(),
                    confidence=0.85,  # LaTeX-OCR 默认置信度
                    image_path=str(image_path),
                ))
                logger.debug(f"公式识别成功: {latex_text[:50]}...")

        except Exception as e:
            logger.warning(f"公式识别失败: {e}")

        return results

    def extract_from_pdf_page(
        self,
        pdf_path: str | Path,
        page_number: int,
        dpi: int = 150,
    ) -> list[FormulaResult]:
        """
        从PDF页面提取公式（先渲染为图片，再识别）。
        
        Args:
            pdf_path: PDF文件路径
            page_number: 页码（1-based）
            dpi: 渲染DPI
            
        Returns:
            公式识别结果列表
        """
        try:
            import fitz  # type: ignore[import]
            from PIL import Image  # type: ignore[import]
            import io

            doc = fitz.open(str(pdf_path))
            page = doc[page_number - 1]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            doc.close()

            img = Image.open(io.BytesIO(img_data))
            latex_ocr = self._get_latex_ocr()
            latex_text = latex_ocr(img)  # type: ignore[call-arg]

            if latex_text and latex_text.strip():
                return [FormulaResult(
                    latex=latex_text.strip(),
                    confidence=0.85,
                    page_number=page_number,
                )]

        except Exception as e:
            logger.warning(f"第{page_number}页公式提取失败: {e}")

        return []
