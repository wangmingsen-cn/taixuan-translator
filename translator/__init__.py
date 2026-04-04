"""taixuan_translator.translator — 翻译引擎模块"""
from taixuan_translator.translator.base import BaseTranslationEngine, TranslationResult, BatchTranslationResult
from taixuan_translator.translator.factory import TranslationEngineFactory, get_translator
from taixuan_translator.translator.openai_engine import OpenAITranslationEngine
from taixuan_translator.translator.deepl_engine import DeepLTranslationEngine
from taixuan_translator.translator.ollama_engine import OllamaTranslationEngine

__all__ = [
    "BaseTranslationEngine",
    "TranslationResult",
    "BatchTranslationResult",
    "TranslationEngineFactory",
    "get_translator",
    "OpenAITranslationEngine",
    "DeepLTranslationEngine",
    "OllamaTranslationEngine",
]
