"""
太玄智译 - 翻译引擎抽象基类
所有翻译引擎必须继承此类并实现 translate / translate_batch 方法
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from taixuan_translator.core.config import get_settings
from taixuan_translator.data.cache import get_cache_manager


@dataclass
class TranslationResult:
    """单条翻译结果"""
    source_text: str
    translated_text: str
    engine: str
    source_language: str
    target_language: str
    model_name: str = ""
    tokens_used: int = 0
    from_cache: bool = False
    confidence: float = 1.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        # 空文本输入视为成功（无需翻译）
        if not self.source_text or not self.source_text.strip():
            return self.error is None
        return self.error is None and bool(self.translated_text)


@dataclass
class BatchTranslationResult:
    """批量翻译结果"""
    results: list[TranslationResult] = field(default_factory=list)
    total_tokens: int = 0
    cache_hits: int = 0
    errors: int = 0

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.success_count / len(self.results)


class BaseTranslationEngine(abc.ABC):
    """翻译引擎抽象基类"""

    engine_name: str = "base"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache = get_cache_manager()

    # ─── 抽象方法（子类必须实现）────────────────────────────────────────────

    @abc.abstractmethod
    def _do_translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """执行实际翻译（不含缓存逻辑）"""
        ...

    @abc.abstractmethod
    def validate_config(self) -> bool:
        """验证引擎配置是否有效（API Key等）"""
        ...

    @abc.abstractmethod
    def get_model_name(self) -> str:
        """返回当前使用的模型名称"""
        ...

    # ─── 公共方法 ────────────────────────────────────────────────────────────

    def translate(
        self,
        text: str,
        source_language: str = "auto",
        target_language: str = "zh-Hans",
    ) -> TranslationResult:
        """
        翻译单条文本（含缓存）。
        
        Args:
            text: 待翻译文本
            source_language: 源语言代码（auto=自动检测）
            target_language: 目标语言代码
            
        Returns:
            TranslationResult
        """
        if not text or not text.strip():
            return TranslationResult(
                source_text=text,
                translated_text=text,
                engine=self.engine_name,
                source_language=source_language,
                target_language=target_language,
            )

        model_name = self.get_model_name()

        # 尝试缓存
        cached = self.cache.get(
            text, self.engine_name, source_language, target_language, model_name
        )
        if cached is not None:
            return TranslationResult(
                source_text=text,
                translated_text=cached,
                engine=self.engine_name,
                source_language=source_language,
                target_language=target_language,
                model_name=model_name,
                from_cache=True,
            )

        # 调用实际翻译
        try:
            translated = self._do_translate(text, source_language, target_language)

            # 写入缓存
            self.cache.set(
                text, translated, self.engine_name, source_language, target_language, model_name
            )

            return TranslationResult(
                source_text=text,
                translated_text=translated,
                engine=self.engine_name,
                source_language=source_language,
                target_language=target_language,
                model_name=model_name,
            )

        except Exception as e:
            logger.error(f"[{self.engine_name}] 翻译失败: {e}")
            return TranslationResult(
                source_text=text,
                translated_text="",
                engine=self.engine_name,
                source_language=source_language,
                target_language=target_language,
                model_name=model_name,
                error=str(e),
            )

    def translate_batch(
        self,
        texts: list[str],
        source_language: str = "auto",
        target_language: str = "zh-Hans",
    ) -> BatchTranslationResult:
        """
        批量翻译（默认逐条翻译，子类可重写为并发/批量API调用）。
        
        Args:
            texts: 待翻译文本列表
            source_language: 源语言
            target_language: 目标语言
            
        Returns:
            BatchTranslationResult
        """
        batch_result = BatchTranslationResult()

        for text in texts:
            result = self.translate(text, source_language, target_language)
            batch_result.results.append(result)
            batch_result.total_tokens += result.tokens_used
            if result.from_cache:
                batch_result.cache_hits += 1
            if not result.success:
                batch_result.errors += 1

        logger.info(
            f"[{self.engine_name}] 批量翻译完成: "
            f"{batch_result.success_count}/{len(texts)} 成功, "
            f"{batch_result.cache_hits} 缓存命中, "
            f"{batch_result.total_tokens} tokens"
        )
        return batch_result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} engine={self.engine_name} model={self.get_model_name()}>"
