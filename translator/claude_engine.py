"""
太玄智译 - Claude (Anthropic) 翻译引擎
使用 OpenAI 兼容接口调用 Claude API
"""
from __future__ import annotations

import time
from typing import Optional

from loguru import logger

from taixuan_translator.core.exceptions import (
    InvalidAPIKeyError,
    TranslationAPIError,
    TranslationRateLimitError,
    TranslationTimeoutError,
)
from taixuan_translator.translator.base import BaseTranslationEngine

_SYSTEM_PROMPT = """你是专业的学术文献翻译专家。请将以下文本准确翻译为{target_language}。
要求：保持学术严谨性，专业术语使用标准译法，数字/公式/代码保持原样，只输出译文。"""

_LANGUAGE_NAMES = {
    "zh-Hans": "简体中文", "zh-Hant": "繁体中文",
    "en": "英文", "ja": "日文", "ko": "韩文",
    "fr": "法文", "de": "德文", "es": "西班牙文",
}


class ClaudeTranslationEngine(BaseTranslationEngine):
    """Claude (Anthropic) 翻译引擎"""

    engine_name = "claude"

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[object] = None

    def _get_client(self) -> object:
        if self._client is None:
            try:
                import anthropic  # type: ignore[import]
            except ImportError:
                # 降级：使用 openai 兼容接口
                try:
                    from openai import OpenAI  # type: ignore[import]
                    cfg = self.settings.claude
                    if not cfg.api_key:
                        raise InvalidAPIKeyError("Claude")
                    self._client = OpenAI(
                        api_key=cfg.api_key,
                        base_url=cfg.base_url + "/v1",
                        timeout=cfg.timeout,
                        max_retries=0,
                    )
                    return self._client
                except ImportError as e:
                    raise ImportError("请安装 anthropic 或 openai 包") from e

            cfg = self.settings.claude
            if not cfg.api_key:
                raise InvalidAPIKeyError("Claude")
            self._client = anthropic.Anthropic(api_key=cfg.api_key)
        return self._client

    def validate_config(self) -> bool:
        return bool(self.settings.claude.api_key)

    def get_model_name(self) -> str:
        return self.settings.claude.model

    def _do_translate(self, text: str, source_language: str, target_language: str) -> str:
        cfg = self.settings.claude
        lang_name = _LANGUAGE_NAMES.get(target_language, target_language)
        system_prompt = _SYSTEM_PROMPT.format(target_language=lang_name)

        try:
            client = self._get_client()
            # 尝试 anthropic 原生接口
            if hasattr(client, "messages"):
                response = client.messages.create(  # type: ignore[attr-defined]
                    model=cfg.model,
                    max_tokens=cfg.max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": text}],
                )
                return response.content[0].text.strip()
            else:
                # OpenAI 兼容接口
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
            if "401" in err or "unauthorized" in err or "invalid" in err:
                raise InvalidAPIKeyError("Claude") from e
            if "429" in err or "rate" in err:
                raise TranslationRateLimitError("Claude") from e
            raise TranslationAPIError("Claude", detail=str(e)) from e
