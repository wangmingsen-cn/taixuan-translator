"""
太玄智译 - DeepSeek 翻译引擎
支持 DeepSeek Chat API
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

# 翻译系统提示词
_SYSTEM_PROMPT = """你是一位专业的学术文献翻译专家，精通中英文双语翻译。

翻译要求：
1. 准确传达原文含义，保持学术严谨性
2. 专业术语使用标准译法，首次出现时可附原文（如：机器学习（Machine Learning））
3. 保持原文的段落结构和格式
4. 数字、公式、代码、专有名词保持原样不翻译
5. 语言流畅自然，符合中文表达习惯
6. 只输出译文，不添加任何解释或注释

请将以下文本翻译为{target_language}："""

_LANGUAGE_NAMES = {
    "zh-Hans": "简体中文",
    "zh-Hant": "繁体中文",
    "en": "英文",
    "ja": "日文",
    "ko": "韩文",
    "fr": "法文",
    "de": "德文",
    "es": "西班牙文",
    "ru": "俄文",
    "ar": "阿拉伯文",
}


class DeepSeekTranslationEngine(BaseTranslationEngine):
    """DeepSeek 翻译引擎"""

    engine_name = "deepseek"

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[object] = None

    def _get_client(self) -> object:
        """懒加载 DeepSeek 客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError("请安装 openai 包: pip install openai") from e

            cfg = self.settings.deepseek
            if not cfg.api_key:
                raise InvalidAPIKeyError("DeepSeek")

            self._client = OpenAI(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
                timeout=cfg.timeout,
                max_retries=0,
            )
        return self._client

    def validate_config(self) -> bool:
        """验证 DeepSeek 配置"""
        return bool(self.settings.deepseek.api_key)

    def get_model_name(self) -> str:
        return self.settings.deepseek.model

    def _do_translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """调用 DeepSeek API 翻译"""
        from openai import APIStatusError, APITimeoutError

        cfg = self.settings.deepseek
        client = self._get_client()
        lang_name = _LANGUAGE_NAMES.get(target_language, target_language)
        system_prompt = _SYSTEM_PROMPT.format(target_language=lang_name)

        last_error: Optional[Exception] = None
        max_retries = cfg.max_retries if hasattr(cfg, 'max_retries') else 3

        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=cfg.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    max_tokens=cfg.max_tokens,
                    temperature=cfg.temperature,
                )
                translated = response.choices[0].message.content or ""
                logger.debug(
                    f"[DeepSeek] 翻译成功, tokens={response.usage.total_tokens if response.usage else 0}"
                )
                return translated.strip()

            except APITimeoutError as e:
                last_error = TranslationTimeoutError("DeepSeek", cfg.timeout)
                logger.warning(f"[DeepSeek] 请求超时 (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

            except APIStatusError as e:
                if e.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    last_error = TranslationRateLimitError("DeepSeek", retry_after)
                    logger.warning(f"[DeepSeek] 限流，{retry_after}s后重试")
                    if attempt < max_retries:
                        time.sleep(min(retry_after, 30))
                elif e.status_code == 401:
                    raise InvalidAPIKeyError("DeepSeek") from e
                else:
                    last_error = TranslationAPIError("DeepSeek", e.status_code, str(e))
                    logger.error(f"[DeepSeek] API错误 {e.status_code}: {e}")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)

            except Exception as e:
                last_error = e
                logger.error(f"[DeepSeek] 未知错误 (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        raise last_error or TranslationAPIError("DeepSeek")
