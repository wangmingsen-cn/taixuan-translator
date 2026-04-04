"""
测试：翻译缓存模块
"""
import pytest
from unittest.mock import patch, MagicMock

from taixuan_translator.data.database import init_database
from taixuan_translator.data.cache import TranslationCacheManager


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """每个测试使用独立的临时数据库"""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("TAIXUAN_DB_PATH", str(db_file))
    
    # 重置全局引擎
    import taixuan_translator.data.database as db_module
    db_module._engine = None
    db_module._SessionFactory = None
    
    init_database()
    yield
    
    db_module._engine = None
    db_module._SessionFactory = None


def test_cache_miss():
    """测试缓存未命中"""
    manager = TranslationCacheManager()
    result = manager.get("hello world", "openai", "en", "zh-Hans")
    assert result is None


def test_cache_set_and_get():
    """测试缓存写入和读取"""
    manager = TranslationCacheManager()
    manager.set("hello world", "你好世界", "openai", "en", "zh-Hans")
    result = manager.get("hello world", "openai", "en", "zh-Hans")
    assert result == "你好世界"


def test_cache_different_engines():
    """测试不同引擎的缓存隔离"""
    manager = TranslationCacheManager()
    manager.set("hello", "你好(openai)", "openai", "en", "zh-Hans")
    manager.set("hello", "你好(deepl)", "deepl", "en", "zh-Hans")
    
    assert manager.get("hello", "openai", "en", "zh-Hans") == "你好(openai)"
    assert manager.get("hello", "deepl", "en", "zh-Hans") == "你好(deepl)"


def test_cache_stats():
    """测试缓存统计"""
    manager = TranslationCacheManager()
    manager.set("test1", "测试1", "openai", "en", "zh-Hans")
    manager.set("test2", "测试2", "openai", "en", "zh-Hans")
    
    stats = manager.get_stats()
    assert stats["total_entries"] >= 2
    assert stats["active_entries"] >= 2


def test_cache_clear_all():
    """测试清空缓存"""
    manager = TranslationCacheManager()
    manager.set("test", "测试", "openai", "en", "zh-Hans")
    count = manager.clear_all()
    assert count >= 1
    assert manager.get("test", "openai", "en", "zh-Hans") is None
