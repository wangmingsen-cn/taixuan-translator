"""
太玄智译 - Ollama 本地翻译引擎
支持 qwen2.5、llama3 等本地模型，完全离线运行
"""
from __future__ import annotations

from typing import Optional

from loguru import logger

from taixuan_translator.core.exceptions import (
    OllamaNotRunningError,
    TranslationAPIError,
    TranslationTimeoutError,
)
from taixuan_translator.translator.base import BaseTranslationEngine

_SYSTEM_PROMPT = """你是专业的学术文献翻译专家。请将用户提供的文本准确翻译为{target_language}。

要求：
- 保持学术严谨性，专业术语使用标准译法
- 数字、公式、代码、专有名词保持原样
- 只输出译文，不添加任何解释"""

_LANGUAGE_NAMES = {
    "zh-Hans": "简体中文",
    "zh-Hant": "繁体中文",
    "en": "英文",
    "ja": "日文",
    "ko": "韩文",
}


class OllamaTranslationEngine(BaseTranslationEngine):
    """Ollama 本地翻译引擎"""

    engine_name = "ollama"

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[object] = None

    def _get_client(self) -> object:
        if self._client is None:
            try:
                from ollama import Client  # type: ignore[import]
            except ImportError as e:
                raise ImportError("请安装 ollama 包: pip install ollama") from e

            cfg = self.settings.ollama
            self._client = Client(host=cfg.base_url)
        return self._client

    def validate_config(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            client = self._get_client()
            client.list()  # type: ignore[attr-defined]
            return True
        except Exception:
            return False

    def get_model_name(self) -> str:
        return self.settings.ollama.model

    def _do_translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """调用 Ollama 本地模型翻译"""
        cfg = self.settings.ollama
        lang_name = _LANGUAGE_NAMES.get(target_language, target_language)
        system_prompt = _SYSTEM_PROMPT.format(target_language=lang_name)

        try:
            client = self._get_client()
            response = client.chat(  # type: ignore[attr-defined]
                model=cfg.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                options={
                    "temperature": 0.3,
                    "num_ctx": cfg.context_window,
                },
            )
            translated = response["message"]["content"] if isinstance(response, dict) else response.message.content
            logger.debug(f"[Ollama/{cfg.model}] 翻译成功: {text[:30]}...")
            return (translated or "").strip()

        except ConnectionRefusedError:
            raise OllamaNotRunningError(cfg.base_url)
        except TimeoutError:
            raise TranslationTimeoutError("Ollama", cfg.timeout)
        except Exception as e:
            err_str = str(e).lower()
            if "connection" in err_str or "refused" in err_str:
                raise OllamaNotRunningError(cfg.base_url)
            raise TranslationAPIError("Ollama", detail=str(e)) from e
