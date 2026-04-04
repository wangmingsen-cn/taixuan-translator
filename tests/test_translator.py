"""
测试：翻译引擎基类
"""
import pytest
from unittest.mock import MagicMock, patch

from taixuan_translator.translator.base import BaseTranslationEngine, TranslationResult


class MockEngine(BaseTranslationEngine):
    """测试用Mock引擎"""
    engine_name = "mock"

    def _do_translate(self, text, source_language, target_language):
        return f"[TRANSLATED] {text}"

    def validate_config(self):
        return True

    def get_model_name(self):
        return "mock-model"


def test_translate_empty_text():
    """空文本直接返回，不调用翻译"""
    engine = MockEngine()
    result = engine.translate("", "en", "zh-Hans")
    assert result.translated_text == ""
    assert result.success


def test_translate_success():
    """正常翻译流程"""
    engine = MockEngine()
    result = engine.translate("Hello World", "en", "zh-Hans")
    assert result.success
    assert "[TRANSLATED]" in result.translated_text
    assert result.engine == "mock"


def test_translate_batch():
    """批量翻译"""
    engine = MockEngine()
    texts = ["Hello", "World", "Python"]
    batch = engine.translate_batch(texts, "en", "zh-Hans")
    assert len(batch.results) == 3
    assert batch.success_count == 3
    assert batch.success_rate == 1.0


def test_translate_error_handling():
    """翻译失败时返回错误结果而非抛出异常"""
    class FailEngine(MockEngine):
        def _do_translate(self, text, source_language, target_language):
            raise RuntimeError("API Error")

    engine = FailEngine()
    result = engine.translate("test", "en", "zh-Hans")
    assert not result.success
    assert result.error is not None
