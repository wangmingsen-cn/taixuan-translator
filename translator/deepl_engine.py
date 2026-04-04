"""
太玄智译 - DeepL 翻译引擎
"""
from __future__ import annotations

import time
from typing import Optional

from loguru import logger

from taixuan_translator.core.exceptions import (
    InvalidAPIKeyError,
    TranslationAPIError,
    TranslationQuotaExceededError,
    TranslationRateLimitError,
)
from taixuan_translator.translator.base import BaseTranslationEngine

# DeepL 语言代码映射
_DEEPL_LANG_MAP = {
    "zh-Hans": "ZH",
    "zh-Hant": "ZH",
    "en": "EN-US",
    "ja": "JA",
    "ko": "KO",
    "fr": "FR",
    "de": "DE",
    "es": "ES",
    "ru": "RU",
    "ar": "AR",
    "auto": None,  # DeepL 自动检测
}


class DeepLTranslationEngine(BaseTranslationEngine):
    """DeepL 翻译引擎"""

    engine_name = "deepl"

    def __init__(self) -> None:
        super().__init__()
        self._translator: Optional[object] = None

    def _get_translator(self) -> object:
        """懒加载 DeepL 翻译器"""
        if self._translator is None:
            try:
                import deepl  # type: ignore[import]
            except ImportError as e:
                raise ImportError("请安装 deepl 包: pip install deepl") from e

            cfg = self.settings.deepl
            if not cfg.api_key:
                raise InvalidAPIKeyError("DeepL")

            self._translator = deepl.Translator(
                auth_key=cfg.api_key,
                server_url=cfg.api_url if "api-free" not in cfg.api_url else None,
            )
        return self._translator

    def validate_config(self) -> bool:
        return bool(self.settings.deepl.api_key)

    def get_model_name(self) -> str:
        return "deepl-translate"

    def _do_translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """调用 DeepL API 翻译"""
        try:
            import deepl  # type: ignore[import]
        except ImportError as e:
            raise ImportError("请安装 deepl 包: pip install deepl") from e

        translator = self._get_translator()
        target_lang_code = _DEEPL_LANG_MAP.get(target_language, target_language.upper())
        source_lang_code = _DEEPL_LANG_MAP.get(source_language)  # None = 自动检测

        try:
            result = translator.translate_text(  # type: ignore[attr-defined]
                text,
                source_lang=source_lang_code,
                target_lang=target_lang_code,
                preserve_formatting=True,
            )
            translated = result.text if hasattr(result, "text") else str(result)
            logger.debug(f"[DeepL] 翻译成功: {text[:30]}... → {translated[:30]}...")
            return translated

        except deepl.QuotaExceededException:
            raise TranslationQuotaExceededError("DeepL")
        except deepl.TooManyRequestsException:
            raise TranslationRateLimitError("DeepL", retry_after=60)
        except deepl.AuthorizationException:
            raise InvalidAPIKeyError("DeepL")
        except Exception as e:
            raise TranslationAPIError("DeepL", detail=str(e)) from e
