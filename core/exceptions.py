"""
太玄智译 - 自定义异常体系
统一异常分类，便于上层捕获和用户提示
"""
from __future__ import annotations


class TaixuanBaseError(Exception):
    """所有太玄智译异常的基类"""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", detail: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.detail = detail

    def __str__(self) -> str:
        if self.detail:
            return f"[{self.code}] {self.message} — {self.detail}"
        return f"[{self.code}] {self.message}"


# ─── PDF 解析异常 ────────────────────────────────────────────────────────────

class PDFParseError(TaixuanBaseError):
    """PDF解析失败"""
    def __init__(self, message: str = "PDF解析失败", detail: str = "") -> None:
        super().__init__(message, "PDF_PARSE_ERROR", detail)


class PDFEncryptedError(PDFParseError):
    """PDF文件已加密"""
    def __init__(self, path: str = "") -> None:
        super().__init__(
            "PDF文件已加密，请先解密后再翻译",
            detail=f"文件路径: {path}"
        )
        self.code = "PDF_ENCRYPTED"


class PDFCorruptedError(PDFParseError):
    """PDF文件损坏"""
    def __init__(self, path: str = "") -> None:
        super().__init__(
            "PDF文件已损坏或格式不正确",
            detail=f"文件路径: {path}"
        )
        self.code = "PDF_CORRUPTED"


class LayoutAnalysisError(PDFParseError):
    """布局分析失败"""
    def __init__(self, page: int = 0, detail: str = "") -> None:
        super().__init__(
            f"第{page}页布局分析失败",
            detail=detail
        )
        self.code = "LAYOUT_ANALYSIS_ERROR"
        self.page = page


class FormulaExtractionError(PDFParseError):
    """公式提取失败"""
    def __init__(self, detail: str = "") -> None:
        super().__init__("公式提取失败", detail=detail)
        self.code = "FORMULA_EXTRACTION_ERROR"


class TableExtractionError(PDFParseError):
    """表格提取失败"""
    def __init__(self, detail: str = "") -> None:
        super().__init__("表格提取失败", detail=detail)
        self.code = "TABLE_EXTRACTION_ERROR"


# ─── 翻译引擎异常 ────────────────────────────────────────────────────────────

class TranslationError(TaixuanBaseError):
    """翻译失败基类"""
    def __init__(self, message: str = "翻译失败", code: str = "TRANSLATION_ERROR", detail: str = "") -> None:
        super().__init__(message, code, detail)


class TranslationAPIError(TranslationError):
    """翻译API调用失败"""
    def __init__(self, engine: str, status_code: int = 0, detail: str = "") -> None:
        super().__init__(
            f"{engine} API调用失败（HTTP {status_code}）",
            code="TRANSLATION_API_ERROR",
            detail=detail,
        )
        self.engine = engine
        self.status_code = status_code


class TranslationRateLimitError(TranslationError):
    """翻译API限流"""
    def __init__(self, engine: str, retry_after: int = 60) -> None:
        super().__init__(
            f"{engine} API请求频率超限，请{retry_after}秒后重试",
            code="TRANSLATION_RATE_LIMIT",
        )
        self.engine = engine
        self.retry_after = retry_after


class TranslationQuotaExceededError(TranslationError):
    """翻译配额耗尽"""
    def __init__(self, engine: str) -> None:
        super().__init__(
            f"{engine} API配额已耗尽，请检查账户余额或切换翻译引擎",
            code="TRANSLATION_QUOTA_EXCEEDED",
        )
        self.engine = engine


class TranslationTimeoutError(TranslationError):
    """翻译请求超时"""
    def __init__(self, engine: str, timeout: int = 60) -> None:
        super().__init__(
            f"{engine} 翻译请求超时（{timeout}s），请检查网络或切换引擎",
            code="TRANSLATION_TIMEOUT",
        )
        self.engine = engine


class OllamaNotRunningError(TranslationError):
    """Ollama服务未启动"""
    def __init__(self, url: str = "http://localhost:11434") -> None:
        super().__init__(
            f"Ollama服务未运行，请先启动Ollama（{url}）",
            code="OLLAMA_NOT_RUNNING",
        )


class InvalidAPIKeyError(TranslationError):
    """API Key无效"""
    def __init__(self, engine: str) -> None:
        super().__init__(
            f"{engine} API Key无效或未配置，请在设置中填写正确的API Key",
            code="INVALID_API_KEY",
        )
        self.engine = engine


# ─── Word生成异常 ────────────────────────────────────────────────────────────

class DocxGenerationError(TaixuanBaseError):
    """Word文档生成失败"""
    def __init__(self, message: str = "Word文档生成失败", detail: str = "") -> None:
        super().__init__(message, "DOCX_GENERATION_ERROR", detail)


class TemplateNotFoundError(DocxGenerationError):
    """Word模板文件不存在"""
    def __init__(self, template_path: str) -> None:
        super().__init__(
            f"Word模板文件不存在: {template_path}",
            detail="请检查模板文件是否完整"
        )
        self.code = "TEMPLATE_NOT_FOUND"


# ─── 数据库异常 ──────────────────────────────────────────────────────────────

class DatabaseError(TaixuanBaseError):
    """数据库操作失败"""
    def __init__(self, message: str = "数据库操作失败", detail: str = "") -> None:
        super().__init__(message, "DATABASE_ERROR", detail)


class RecordNotFoundError(DatabaseError):
    """记录不存在"""
    def __init__(self, model: str, record_id: int | str) -> None:
        super().__init__(
            f"{model} 记录不存在（ID: {record_id}）",
            detail="请检查记录ID是否正确"
        )
        self.code = "RECORD_NOT_FOUND"


# ─── 文件操作异常 ────────────────────────────────────────────────────────────

class FileOperationError(TaixuanBaseError):
    """文件操作失败"""
    def __init__(self, message: str = "文件操作失败", detail: str = "") -> None:
        super().__init__(message, "FILE_OPERATION_ERROR", detail)


class UnsupportedFileTypeError(FileOperationError):
    """不支持的文件类型"""
    def __init__(self, file_path: str, supported: list[str] | None = None) -> None:
        supported_str = "、".join(supported) if supported else "PDF/Word/ePub/HTML/TXT/SRT"
        super().__init__(
            f"不支持的文件类型: {file_path}",
            detail=f"支持的格式: {supported_str}"
        )
        self.code = "UNSUPPORTED_FILE_TYPE"


class FileTooLargeError(FileOperationError):
    """文件过大"""
    def __init__(self, file_path: str, size_mb: float, max_mb: float = 500) -> None:
        super().__init__(
            f"文件过大（{size_mb:.1f}MB），超过限制（{max_mb}MB）",
            detail=f"文件路径: {file_path}"
        )
        self.code = "FILE_TOO_LARGE"


# ─── 配置异常 ────────────────────────────────────────────────────────────────

class ConfigError(TaixuanBaseError):
    """配置错误"""
    def __init__(self, message: str = "配置错误", detail: str = "") -> None:
        super().__init__(message, "CONFIG_ERROR", detail)
