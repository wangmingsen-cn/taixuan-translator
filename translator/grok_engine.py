"""
太玄智译 - Grok (xAI) 翻译引擎
使用 xAI OpenAI 兼容接口
"""
from __future__ import annotations

from typing import Optional

from loguru import logger

from taixuan_translator.core.exceptions import InvalidAPIKeyError, TranslationAPIError
from taixuan_translator.translator.base import BaseTranslationEngine

_SYSTEM_PROMPT = "你是专业的学术文献翻译专家。请将以下文本准确翻译为{target_language}。要求：保持学术严谨性，只输出译文。"

_LANGUAGE_NAMES = {
    "zh-Hans": "简体中文", "zh-Hant": "繁体中文",
    "en": "英文", "ja": "日文", "ko": "韩文",
}


class GrokTranslationEngine(BaseTranslationEngine):
    """Grok (xAI) 翻译引擎"""

    engine_name = "grok"

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[object] = None

    def _get_client(self) -> object:
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore[import]
            except ImportError as e:
                raise ImportError("请安装 openai 包: pip install openai") from e

            cfg = self.settings.grok
            if not cfg.api_key:
                raise InvalidAPIKeyError("Grok")

            self._client = OpenAI(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
                timeout=cfg.timeout,
                max_retries=0,
            )
        return self._client

    def validate_config(self) -> bool:
        return bool(self.settings.grok.api_key)

    def get_model_name(self) -> str:
        return self.settings.grok.model

    def _do_translate(self, text: str, source_language: str, target_language: str) -> str:
        cfg = self.settings.grok
        lang_name = _LANGUAGE_NAMES.get(target_language, target_language)
        system_prompt = _SYSTEM_PROMPT.format(target_language=lang_name)

        try:
            client = self._get_client()
            response = client.chat.completions.create(  # type: ignore[attr-defined]
                model=cfg.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            err = str(e).lower()
            if "401" in err or "unauthorized" in err:
                raise InvalidAPIKeyError("Grok") from e
            raise TranslationAPIError("Grok", detail=str(e)) from e
