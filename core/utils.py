"""
太玄智译 - 日志系统 & 通用工具函数
"""
from __future__ import annotations

import hashlib
import re
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

from loguru import logger

from taixuan_translator.core.config import get_settings

F = TypeVar("F", bound=Callable[..., Any])


# ─── 日志初始化 ──────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """初始化 loguru 日志系统"""
    settings = get_settings()
    log_dir = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    # 移除默认handler
    logger.remove()

    # 控制台输出（彩色）
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # 文件输出（按天轮转，保留30天）
    logger.add(
        log_dir / "taixuan_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    # 错误日志单独记录
    logger.add(
        log_dir / "error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="90 days",
        encoding="utf-8",
    )

    logger.info(f"日志系统初始化完成，日志目录: {log_dir}")


# ─── 装饰器工具 ──────────────────────────────────────────────────────────────

def timeit(func: F) -> F:
    """计时装饰器，记录函数执行时间"""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__qualname__} 执行耗时: {elapsed:.3f}s")
        return result
    return wrapper  # type: ignore[return-value]


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """重试装饰器（指数退避）"""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            current_delay = delay
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"{func.__qualname__} 重试{max_attempts}次后仍失败: {e}")
                        raise
                    logger.warning(
                        f"{func.__qualname__} 第{attempt}次失败，{current_delay:.1f}s后重试: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper  # type: ignore[return-value]
    return decorator


# ─── 文件工具 ────────────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {
    ".pdf": "PDF文档",
    ".docx": "Word文档",
    ".doc": "Word文档（旧版）",
    ".epub": "ePub电子书",
    ".html": "HTML网页",
    ".htm": "HTML网页",
    ".txt": "纯文本",
    ".srt": "SRT字幕",
    ".ass": "ASS字幕",
    ".ssa": "SSA字幕",
}


def get_file_type(path: str | Path) -> str:
    """获取文件类型描述"""
    ext = Path(path).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext, "未知格式")


def is_supported_file(path: str | Path) -> bool:
    """检查文件格式是否支持"""
    ext = Path(path).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def get_file_size_mb(path: str | Path) -> float:
    """获取文件大小（MB）"""
    return Path(path).stat().st_size / (1024 * 1024)


def compute_file_hash(path: str | Path, algorithm: str = "md5") -> str:
    """计算文件哈希值（用于缓存键）"""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str, max_length: int = 200) -> str:
    """将字符串转换为安全的文件名"""
    # 替换Windows不允许的字符
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    # 去除首尾空格和点
    name = name.strip(". ")
    # 截断过长文件名
    if len(name) > max_length:
        name = name[:max_length]
    return name or "untitled"


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在，不存在则创建"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─── 文本工具 ────────────────────────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = 2000) -> list[str]:
    """
    将长文本按段落分块，每块不超过 max_chars 字符。
    优先在段落边界（双换行）切分，其次在句子边界切分。
    """
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}".lstrip("\n")
        else:
            if current:
                chunks.append(current.strip())
            # 段落本身超长，按句子切分
            if len(para) > max_chars:
                sentences = re.split(r"(?<=[.!?。！？])\s+", para)
                sub = ""
                for sent in sentences:
                    if len(sub) + len(sent) + 1 <= max_chars:
                        sub = f"{sub} {sent}".lstrip()
                    else:
                        if sub:
                            chunks.append(sub.strip())
                        sub = sent
                if sub:
                    current = sub
                else:
                    current = ""
            else:
                current = para

    if current:
        chunks.append(current.strip())

    return [c for c in chunks if c]


def detect_language(text: str) -> str:
    """
    简单语言检测（基于字符集统计）。
    生产环境建议替换为 langdetect 或 fasttext。
    """
    if not text:
        return "unknown"

    sample = text[:500]
    cjk_count = sum(1 for c in sample if "\u4e00" <= c <= "\u9fff")
    latin_count = sum(1 for c in sample if c.isascii() and c.isalpha())

    if cjk_count / max(len(sample), 1) > 0.2:
        return "zh"
    if latin_count / max(len(sample), 1) > 0.5:
        return "en"
    return "unknown"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本用于日志/UI显示"""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


# ─── 进度回调类型 ────────────────────────────────────────────────────────────

class ProgressCallback:
    """进度回调封装，供后端模块向UI层汇报进度"""

    def __init__(self, callback: Callable[[int, int, str], None] | None = None) -> None:
        self._callback = callback
        self._current = 0
        self._total = 0

    def set_total(self, total: int) -> None:
        self._total = total

    def update(self, current: int, message: str = "") -> None:
        self._current = current
        if self._callback:
            self._callback(current, self._total, message)
        logger.debug(f"进度: {current}/{self._total} {message}")

    def increment(self, message: str = "") -> None:
        self.update(self._current + 1, message)

    @property
    def percent(self) -> float:
        if self._total == 0:
            return 0.0
        return self._current / self._total * 100
