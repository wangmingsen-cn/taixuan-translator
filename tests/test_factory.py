"""
测试：翻译引擎工厂 - 10个引擎注册与加载
"""
import pytest
from unittest.mock import patch, MagicMock

from taixuan_translator.translator.factory import TranslationEngineFactory, _ENGINE_REGISTRY
from taixuan_translator.translator.base import BaseTranslationEngine


def test_all_engines_registered():
    """测试10个引擎全部注册"""
    expected = {"openai", "deepseek", "deepl", "ollama", "claude",
                "qwen", "minimax", "gemini", "grok", "custom"}
    actual = set(TranslationEngineFactory.list_all_engines())
    assert expected == actual, f"引擎注册不完整，缺少: {expected - actual}"


def test_engine_registry_entries():
    """测试注册表每个条目格式正确"""
    for name, (module_path, class_name) in _ENGINE_REGISTRY.items():
        assert module_path.startswith("taixuan_translator.translator."), \
            f"{name}: module_path 格式错误"
        assert class_name.endswith("TranslationEngine"), \
            f"{name}: class_name 格式错误"


def test_get_engine_openai():
    """测试获取 OpenAI 引擎实例"""
    engine = TranslationEngineFactory.get_engine("openai")
    assert engine.engine_name == "openai"
    assert isinstance(engine, BaseTranslationEngine)


def test_get_engine_deepseek():
    """测试获取 DeepSeek 引擎实例（当前默认）"""
    engine = TranslationEngineFactory.get_engine("deepseek")
    assert engine.engine_name == "deepseek"
    assert "deepseek" in engine.get_model_name()


def test_get_engine_ollama():
    """测试获取 Ollama 引擎实例"""
    engine = TranslationEngineFactory.get_engine("ollama")
    assert engine.engine_name == "ollama"


def test_get_engine_invalid():
    """测试无效引擎名抛出 ValueError"""
    with pytest.raises(ValueError, match="不支持的翻译引擎"):
        TranslationEngineFactory.get_engine("nonexistent_engine")


def test_engine_singleton():
    """测试同一引擎返回同一实例（单例缓存）"""
    TranslationEngineFactory.reset()
    e1 = TranslationEngineFactory.get_engine("openai")
    e2 = TranslationEngineFactory.get_engine("openai")
    assert e1 is e2


def test_engine_reset():
    """测试 reset 后重新创建实例"""
    e1 = TranslationEngineFactory.get_engine("openai")
    TranslationEngineFactory.reset()
    e2 = TranslationEngineFactory.get_engine("openai")
    assert e1 is not e2


def test_get_default_engine():
    """测试获取默认引擎（应为 deepseek）"""
    engine = TranslationEngineFactory.get_default_engine()
    assert engine.engine_name == "deepseek"


def test_all_engines_instantiable():
    """测试所有引擎均可实例化（不依赖 API Key）"""
    TranslationEngineFactory.reset()
    for name in TranslationEngineFactory.list_all_engines():
        try:
            engine = TranslationEngineFactory.get_engine(name)
            assert isinstance(engine, BaseTranslationEngine), \
                f"{name}: 不是 BaseTranslationEngine 子类"
            assert engine.engine_name == name, \
                f"{name}: engine_name 不匹配"
        except Exception as e:
            pytest.fail(f"引擎 {name} 实例化失败: {e}")
