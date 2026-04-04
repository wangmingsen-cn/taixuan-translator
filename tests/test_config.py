"""
测试：核心配置模块
"""
import pytest
from taixuan_translator.core.config import get_settings, TranslationEngine, TargetLanguage


def test_default_settings():
    """测试默认配置加载"""
    settings = get_settings()
    assert settings.app_name == "太玄智译"
    assert settings.app_version == "1.0.0"
    # 架构师已将默认引擎调整为 DeepSeek（TX-PM-2026-004）
    assert settings.default_engine == TranslationEngine.DEEPSEEK
    assert settings.target_language == TargetLanguage.ZH_HANS


def test_settings_singleton():
    """测试配置单例"""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_openai_settings():
    """测试OpenAI子配置"""
    settings = get_settings()
    assert settings.openai.model == "gpt-4o-mini"
    assert settings.openai.max_retries == 3
    assert 0 <= settings.openai.temperature <= 1


def test_deepseek_settings():
    """测试DeepSeek子配置（当前默认引擎）"""
    settings = get_settings()
    assert "deepseek" in settings.deepseek.base_url
    assert settings.deepseek.model == "deepseek-chat"
    assert settings.deepseek.max_retries == 3
    assert 0 <= settings.deepseek.temperature <= 1


def test_docx_settings():
    """测试Word生成配置"""
    settings = get_settings()
    assert settings.docx.font_name_cn == "宋体"
    assert settings.docx.font_size_body > 0
    assert settings.docx.line_spacing > 0


def test_all_engines_defined():
    """测试10个引擎枚举均已定义"""
    expected = {"openai", "deepseek", "deepl", "ollama", "claude", "qwen", "minimax", "gemini", "grok", "custom"}
    actual = {e.value for e in TranslationEngine}
    assert expected == actual, f"引擎枚举不完整，缺少: {expected - actual}"


def test_engine_sub_configs_exist():
    """测试各引擎子配置均可访问"""
    settings = get_settings()
    assert hasattr(settings, "openai")
    assert hasattr(settings, "deepseek")
    assert hasattr(settings, "deepl")
    assert hasattr(settings, "ollama")
    # 扩展引擎（按需配置）
    for attr in ("claude", "qwen", "minimax"):
        assert hasattr(settings, attr), f"缺少引擎配置: {attr}"
