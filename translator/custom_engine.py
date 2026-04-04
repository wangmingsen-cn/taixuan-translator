"""
太玄智译 - 自定义翻译引擎
支持任意 OpenAI 兼容接口（出版集团自建模型、私有部署等）
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


class CustomTranslationEngine(BaseTranslationEngine):
    """
    自定义翻译引擎（OpenAI 兼容接口）
    
    适用场景：
    - 出版集团自建翻译模型
    - 私有化部署的 LLM 服务
    - 第三方 OpenAI 兼容 API
    
    配置方式（.env）：
        CUSTOM_API_KEY=your-key
        CUSTOM_BASE_URL=https://your-api.example.com/v1
        CUSTOM_MODEL=your-model-name
    """

    engine_name = "custom"

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[object] = None

    def _get_client(self) -> object:
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore[import]
            except ImportError as e:
                raise ImportError("请安装 openai 包: pip install openai") from e

            cfg = self.settings.custom
            if not cfg.base_url:
                raise TranslationAPIError("Custom", detail="请配置 CUSTOM_BASE_URL")

            self._client = OpenAI(
                api_key=cfg.api_key or "not-required",
                base_url=cfg.base_url,
                timeout=cfg.timeout,
                max_retries=0,
            )
        return self._client

    def validate_config(self) -> bool:
        cfg = self.settings.custom
        return bool(cfg.base_url and cfg.model)

    def get_model_name(self) -> str:
        return self.settings.custom.model

    def _do_translate(self, text: str, source_language: str, target_language: str) -> str:
        cfg = self.settings.custom
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
            raise TranslationAPIError("Custom", detail=str(e)) from e
