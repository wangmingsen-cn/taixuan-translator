"""
太玄智译 - 翻译引擎工厂
统一管理10个引擎实例，支持运行时切换
"""
from __future__ import annotations

from loguru import logger

from taixuan_translator.core.config import TranslationEngine, get_settings
from taixuan_translator.translator.base import BaseTranslationEngine

# 引擎注册表：engine_name → (module_path, class_name)
_ENGINE_REGISTRY: dict[str, tuple[str, str]] = {
    "openai":   ("taixuan_translator.translator.openai_engine",   "OpenAITranslationEngine"),
    "deepseek": ("taixuan_translator.translator.deepseek_engine", "DeepSeekTranslationEngine"),
    "deepl":    ("taixuan_translator.translator.deepl_engine",    "DeepLTranslationEngine"),
    "ollama":   ("taixuan_translator.translator.ollama_engine",   "OllamaTranslationEngine"),
    "claude":   ("taixuan_translator.translator.claude_engine",   "ClaudeTranslationEngine"),
    "qwen":     ("taixuan_translator.translator.qwen_engine",     "QwenTranslationEngine"),
    "minimax":  ("taixuan_translator.translator.minimax_engine",  "MiniMaxTranslationEngine"),
    "gemini":   ("taixuan_translator.translator.gemini_engine",   "GeminiTranslationEngine"),
    "grok":     ("taixuan_translator.translator.grok_engine",     "GrokTranslationEngine"),
    "custom":   ("taixuan_translator.translator.custom_engine",   "CustomTranslationEngine"),
}


class TranslationEngineFactory:
    """翻译引擎工厂（单例缓存 + 懒加载）"""

    _instances: dict[str, BaseTranslationEngine] = {}

    @classmethod
    def get_engine(cls, engine_type: TranslationEngine | str) -> BaseTranslationEngine:
        """
        获取翻译引擎实例（懒加载 + 缓存）。
        
        Args:
            engine_type: 引擎名称（openai/deepseek/deepl/ollama/claude/qwen/minimax/gemini/grok/custom）
            
        Returns:
            对应的翻译引擎实例
            
        Raises:
            ValueError: 不支持的引擎名称
        """
        key = str(engine_type).lower()
        # 处理枚举值
        if hasattr(engine_type, "value"):
            key = engine_type.value  # type: ignore[union-attr]

        if key not in cls._instances:
            cls._instances[key] = cls._create_engine(key)
            logger.info(f"翻译引擎已初始化: {key} ({cls._instances[key].get_model_name()})")

        return cls._instances[key]

    @classmethod
    def _create_engine(cls, engine_name: str) -> BaseTranslationEngine:
        """动态导入并实例化引擎"""
        if engine_name not in _ENGINE_REGISTRY:
            available = list(_ENGINE_REGISTRY.keys())
            raise ValueError(
                f"不支持的翻译引擎: '{engine_name}'，"
                f"可用引擎: {available}"
            )

        module_path, class_name = _ENGINE_REGISTRY[engine_name]
        try:
            import importlib
            module = importlib.import_module(module_path)
            engine_cls: type[BaseTranslationEngine] = getattr(module, class_name)
            return engine_cls()
        except ImportError as e:
            raise ImportError(
                f"引擎 '{engine_name}' 依赖未安装: {e}\n"
                f"请运行: pip install -e '.[dev]'"
            ) from e

    @classmethod
    def get_default_engine(cls) -> BaseTranslationEngine:
        """获取默认翻译引擎（由配置决定）"""
        settings = get_settings()
        return cls.get_engine(settings.default_engine)

    @classmethod
    def list_all_engines(cls) -> list[str]:
        """列出所有已注册的引擎名称"""
        return list(_ENGINE_REGISTRY.keys())

    @classmethod
    def list_configured_engines(cls) -> list[str]:
        """列出已配置（可用）的引擎"""
        configured = []
        for name in _ENGINE_REGISTRY:
            try:
                engine = cls.get_engine(name)
                if engine.validate_config():
                    configured.append(name)
            except Exception:
                pass
        return configured

    @classmethod
    def reset(cls) -> None:
        """重置所有引擎实例（配置变更后调用）"""
        cls._instances.clear()
        logger.info("翻译引擎实例已全部重置")


def get_translator(engine: str | None = None) -> BaseTranslationEngine:
    """便捷函数：获取翻译引擎"""
    if engine:
        return TranslationEngineFactory.get_engine(engine)
    return TranslationEngineFactory.get_default_engine()
