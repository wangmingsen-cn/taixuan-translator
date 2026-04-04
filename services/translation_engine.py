#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation Engine Batch Processor
太玄智译 - 翻译引擎批量处理与质量评估模块

支持引擎: OpenAI GPT, DeepL, Ollama (本地)
功能: 批量翻译段落 + 质量评估对比
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import json
import time
import asyncio
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
# 导入项目配置系统
import sys
sys.path.insert(0, r"C:\Users\29494\.qclaw\workspace\taixuan_translator")

from core.config import get_settings, TranslationEngine

# 加载项目配置
_app_settings = get_settings()

CONFIG = {
    "input_file": r"C:\Users\29494\.qclaw\workspace\data_analysis\pdf_ocr_output\sections_full.json",
    "eval_file": r"C:\Users\29494\.qclaw\workspace\data_analysis\pdf_ocr_output\translation_eval_dataset.json",
    "output_dir": r"C:\Users\29494\.qclaw\workspace\taixuan_translator\translator\output",
    
    # 翻译设置
    "source_lang": "EN",
    "target_lang": "ZH",
    "batch_size": _app_settings.batch_size,
    "max_workers": _app_settings.max_concurrent,
    
    # 引擎配置 (使用项目配置系统)
    "engines": {
        "demo": {
            "enabled": False,
            "description": "Demo mode for testing without API keys"
        },
        "deepseek": {
            "enabled": _app_settings.deepseek.enabled,
            "description": "DeepSeek API (default)",
            "config": _app_settings.deepseek
        },
        "openai": {
            "enabled": _app_settings.openai.enabled,
            "description": "OpenAI GPT",
            "config": _app_settings.openai
        },
        "deepl": {
            "enabled": _app_settings.deepl.enabled,
            "description": "DeepL API",
            "config": _app_settings.deepl
        },
        "ollama": {
            "enabled": _app_settings.ollama.enabled,
            "description": "Ollama local model",
            "config": _app_settings.ollama
        }
    },
    
    # 质量评估配置
    "eval_sample_size": 50,
    "cache_enabled": _app_settings.enable_cache,
    "cache_dir": str(_app_settings.cache_dir)
}


# ==================== 数据模型 ====================
@dataclass
class TranslationResult:
    """翻译结果"""
    para_id: str
    source_text: str
    translated_text: str
    engine: str
    char_count_src: int
    char_count_tgt: int
    processing_time_ms: float
    status: str  # success, failed, cached
    error: Optional[str] = None


@dataclass
class QualityMetrics:
    """质量指标"""
    engine: str
    avg_char_ratio: float  # 译文/原文字符比
    avg_processing_time_ms: float
    total_translated: int
    success_rate: float
    samples: List[Dict]


@dataclass
class BatchResult:
    """批量处理结果"""
    engine: str
    total_paras: int
    success_count: int
    failed_count: int
    total_time_seconds: float
    results: List[Dict]
    metrics: Dict


# ==================== 翻译引擎基类 ====================
class BaseTranslator(ABC):
    """翻译引擎抽象基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__.replace("Translator", "").lower()
    
    @abstractmethod
    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "ZH") -> str:
        """执行单次翻译"""
        pass
    
    def translate_batch(self, texts: List[str], source_lang: str = "EN", 
                       target_lang: str = "ZH") -> List[Tuple[str, str]]:
        """批量翻译（默认实现，可被子类优化）"""
        results = []
        for text in texts:
            try:
                translated = self.translate(text, source_lang, target_lang)
                results.append((text, translated))
            except Exception as e:
                print(f"  [WARN] Translation failed: {e}")
                results.append((text, ""))
        return results


# ==================== 演示模式翻译器 ====================
class DemoTranslator(BaseTranslator):
    """演示模式翻译器（无API密钥时使用）"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "demo"
        print(f"[DEMO] Demo translator initialized (simulates translations)")
    
    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "ZH") -> str:
        """模拟翻译：添加标记返回"""
        # 简单反转/添加标记作为演示
        if len(text) > 100:
            preview = text[:100]
        else:
            preview = text
        
        demo_translation = f"[ZH-CN] {preview}..."
        # 模拟处理延迟
        time.sleep(0.05)
        return demo_translation


# ==================== DeepSeek翻译器 ====================
class DeepSeekTranslator(BaseTranslator):
    """DeepSeek 翻译引擎（默认启用）"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.config_obj = config.get("config", None)
        
        if self.config_obj:
            self.api_key = self.config_obj.api_key
            self.base_url = self.config_obj.base_url
            self.model = self.config_obj.model
            self.max_tokens = self.config_obj.max_tokens
            self.temperature = self.config_obj.temperature
            self.timeout = self.config_obj.timeout
            self.max_retries = self.config_obj.max_retries
        else:
            # Fallback to environment
            self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            self.base_url = "https://api.deepseek.com/v1"
            self.model = "deepseek-chat"
            self.max_tokens = 4096
            self.temperature = 0.3
            self.timeout = 60
            self.max_retries = 3
        
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            print(f"[OK] DeepSeek client initialized: {self.model}")
        except ImportError:
            raise ImportError("openai package not installed")
    
    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "ZH") -> str:
        """使用DeepSeek API翻译"""
        lang_map = {"EN": "English", "ZH": "Chinese", "ZH-Hans": "Chinese (Simplified)"}
        src_name = lang_map.get(source_lang, source_lang)
        tgt_name = lang_map.get(target_lang, target_lang)
        
        prompt = f"""Translate the following {src_name} text to {tgt_name}.
Only output the translation, no explanations or quotes.

Text to translate:
{text}

{tgt_name} translation:"""
        
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate {src_name} to {tgt_name} accurately."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        translated = response.choices[0].message.content.strip()
        
        return translated


# ==================== OpenAI翻译器 ====================
class OpenAITranslator(BaseTranslator):
    """OpenAI GPT翻译引擎"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = os.environ.get(config.get("api_key_env", "OPENAI_API_KEY"))
        self.model = config.get("model", "gpt-4o-mini")
        self.max_tokens = config.get("max_tokens", 2000)
        self.temperature = config.get("temperature", 0.3)
        
        if not self.api_key:
            raise ValueError(f"API key not found: {config.get('api_key_env')}")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            print(f"[OK] OpenAI client initialized: {self.model}")
        except ImportError:
            raise ImportError("openai package not installed: pip install openai")
    
    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "ZH") -> str:
        """使用OpenAI API翻译"""
        lang_map = {"EN": "English", "ZH": "Chinese"}
        src_name = lang_map.get(source_lang, source_lang)
        tgt_name = lang_map.get(target_lang, target_lang)
        
        prompt = f"""Translate the following {src_name} text to {tgt_name}.
Only output the translation, no explanations or quotes.

Text to translate:
{text}

{tgt_name} translation:"""
        
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate {src_name} to {tgt_name} accurately."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        translated = response.choices[0].message.content.strip()
        
        return translated


# ==================== DeepL翻译器 ====================
class DeepLTranslator(BaseTranslator):
    """DeepL翻译引擎"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = os.environ.get(config.get("api_key_env", "DEEPL_API_KEY"))
        self.use_free = config.get("use_free_api", False)
        
        if not self.api_key:
            raise ValueError(f"API key not found: {config.get('api_key_env')}")
        
        try:
            import deepl
            self.client = deepl.Translator(self.api_key)
            print(f"[OK] DeepL client initialized")
        except ImportError:
            raise ImportError("deepl package not installed: pip install deepl")
    
    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "ZH") -> str:
        """使用DeepL API翻译"""
        lang_map = {"EN": "EN-US", "ZH": "ZH-HANS"}
        src_code = lang_map.get(source_lang, "EN-US")
        tgt_code = lang_map.get(target_lang, "ZH-HANS")
        
        result = self.client.translate_text(
            text,
            source_lang=src_code,
            target_lang=tgt_code
        )
        
        return result.text


# ==================== Ollama翻译器 ====================
class OllamaTranslator(BaseTranslator):
    """Ollama本地翻译引擎"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "llama3.2")
        
        try:
            import ollama
            self.client = ollama
            # Test connection
            try:
                self.client.list()
                print(f"[OK] Ollama client initialized: {self.base_url}")
            except:
                print(f"[WARN] Ollama server not reachable at {self.base_url}")
        except ImportError:
            raise ImportError("ollama package not installed: pip install ollama")
    
    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "ZH") -> str:
        """使用Ollama本地模型翻译"""
        lang_map = {"EN": "English", "ZH": "Chinese"}
        src_name = lang_map.get(source_lang, "EN")
        tgt_name = lang_map.get(target_lang, "ZH")
        
        prompt = f"""Translate the following {src_name} text to {tgt_name}.
Only output the translation, no explanations.

{src_name} text:
{text}

{tgt_name} translation:"""
        
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.3}
        )
        
        return response['message']['content'].strip()


# ==================== 翻译引擎工厂 ====================
class TranslatorFactory:
    """翻译引擎工厂"""
    
    @staticmethod
    def create(engine: str, config: dict) -> BaseTranslator:
        """创建翻译引擎实例"""
        engines = {
            "demo": DemoTranslator,
            "deepseek": DeepSeekTranslator,
            "openai": OpenAITranslator,
            "deepl": DeepLTranslator,
            "ollama": OllamaTranslator
        }
        
        engine_class = engines.get(engine.lower())
        if not engine_class:
            raise ValueError(f"Unknown engine: {engine}. Available: {list(engines.keys())}")
        
        return engine_class(config)


# ==================== 缓存管理器 ====================
class TranslationCache:
    """翻译缓存"""
    
    def __init__(self, cache_dir: str, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        self.memory_cache: Dict[str, str] = {}
        
        if enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache()
    
    def _load_cache(self):
        """加载磁盘缓存到内存"""
        cache_file = self.cache_dir / "translations.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.memory_cache = json.load(f)
                print(f"[OK] Loaded {len(self.memory_cache)} cached translations")
            except Exception as e:
                print(f"[WARN] Failed to load cache: {e}")
    
    def _save_cache(self):
        """保存缓存到磁盘"""
        cache_file = self.cache_dir / "translations.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save cache: {e}")
    
    def get(self, text: str, engine: str) -> Optional[str]:
        """获取缓存"""
        if not self.enabled:
            return None
        key = self._make_key(text, engine)
        return self.memory_cache.get(key)
    
    def set(self, text: str, engine: str, translation: str):
        """设置缓存"""
        if not self.enabled:
            return
        key = self._make_key(text, engine)
        self.memory_cache[key] = translation
        
        # 定期保存
        if len(self.memory_cache) % 50 == 0:
            self._save_cache()
    
    def _make_key(self, text: str, engine: str) -> str:
        """生成缓存键"""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{engine}:{text_hash}"
    
    def close(self):
        """关闭时保存缓存"""
        if self.enabled:
            self._save_cache()


# ==================== 批量翻译处理器 ====================
class BatchTranslationProcessor:
    """批量翻译处理器"""
    
    def __init__(self, engine_name: str, engine_config: dict, cache: TranslationCache = None):
        self.engine_name = engine_name
        self.engine_config = engine_config
        self.cache = cache
        self.results: List[TranslationResult] = []
        
        # 创建引擎实例
        try:
            self.engine = TranslatorFactory.create(engine_name, engine_config)
            self.enabled = True
        except Exception as e:
            print(f"[WARN] Engine {engine_name} not available: {e}")
            self.engine = None
            self.enabled = False
    
    def translate_paragraph(self, para: dict) -> TranslationResult:
        """翻译单个段落"""
        para_id = para.get("para_id", f"unknown_{len(self.results)}")
        source_text = para.get("text", para.get("source_text", ""))
        
        if not source_text:
            return TranslationResult(
                para_id=para_id,
                source_text="",
                translated_text="",
                engine=self.engine_name,
                char_count_src=0,
                char_count_tgt=0,
                processing_time_ms=0,
                status="skipped",
                error="Empty source text"
            )
        
        # 检查缓存
        cached = self.cache.get(source_text, self.engine_name) if self.cache else None
        if cached:
            return TranslationResult(
                para_id=para_id,
                source_text=source_text,
                translated_text=cached,
                engine=self.engine_name,
                char_count_src=len(source_text),
                char_count_tgt=len(cached),
                processing_time_ms=0,
                status="cached"
            )
        
        # 执行翻译
        if not self.enabled:
            return TranslationResult(
                para_id=para_id,
                source_text=source_text,
                translated_text="",
                engine=self.engine_name,
                char_count_src=len(source_text),
                char_count_tgt=0,
                processing_time_ms=0,
                status="failed",
                error="Engine not available"
            )
        
        start_time = time.time()
        try:
            translated = self.engine.translate(source_text)
            processing_time = (time.time() - start_time) * 1000
            
            # 保存缓存
            if self.cache:
                self.cache.set(source_text, self.engine_name, translated)
            
            return TranslationResult(
                para_id=para_id,
                source_text=source_text,
                translated_text=translated,
                engine=self.engine_name,
                char_count_src=len(source_text),
                char_count_tgt=len(translated),
                processing_time_ms=processing_time,
                status="success"
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return TranslationResult(
                para_id=para_id,
                source_text=source_text,
                translated_text="",
                engine=self.engine_name,
                char_count_src=len(source_text),
                char_count_tgt=0,
                processing_time_ms=processing_time,
                status="failed",
                error=str(e)
            )
    
    def process_batch(self, paragraphs: List[dict], 
                      progress_callback=None) -> BatchResult:
        """批量处理段落"""
        start_time = time.time()
        
        total = len(paragraphs)
        success_count = 0
        failed_count = 0
        
        results = []
        
        for i, para in enumerate(paragraphs):
            result = self.translate_paragraph(para)
            results.append(asdict(result))
            
            if result.status == "success":
                success_count += 1
            elif result.status == "failed":
                failed_count += 1
            
            if progress_callback:
                progress_callback(i + 1, total)
            
            # 每50个输出进度
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{total} ({100*(i+1)//total}%)")
        
        total_time = time.time() - start_time
        
        # 计算指标
        char_ratio = 0
        avg_time = 0
        if results:
            success_results = [r for r in results if r["status"] == "success"]
            if success_results:
                total_src = sum(r["char_count_src"] for r in success_results)
                total_tgt = sum(r["char_count_tgt"] for r in success_results)
                char_ratio = total_tgt / total_src if total_src > 0 else 0
                avg_time = sum(r["processing_time_ms"] for r in success_results) / len(success_results)
        
        metrics = QualityMetrics(
            engine=self.engine_name,
            avg_char_ratio=char_ratio,
            avg_processing_time_ms=avg_time,
            total_translated=success_count,
            success_rate=success_count / total if total > 0 else 0,
            samples=results[:10]  # 前10个样本
        )
        
        return BatchResult(
            engine=self.engine_name,
            total_paras=total,
            success_count=success_count,
            failed_count=failed_count,
            total_time_seconds=total_time,
            results=results,
            metrics=asdict(metrics)
        )


# ==================== 质量评估器 ====================
class QualityEvaluator:
    """翻译质量评估器"""
    
    @staticmethod
    def evaluate(source_texts: List[str], translated_texts: List[str], 
                 metrics: List[str] = None) -> Dict:
        """
        评估翻译质量
        注意: 需要参考译文才能计算BLEU/ROUGE等指标
        这里提供基础统计指标
        """
        metrics = metrics or ["char_ratio", "avg_length", "success_rate"]
        
        results = {}
        
        if "char_ratio" in metrics:
            ratios = []
            for src, tgt in zip(source_texts, translated_texts):
                if src and tgt:
                    ratios.append(len(tgt) / len(src))
            results["char_ratio"] = {
                "avg": sum(ratios) / len(ratios) if ratios else 0,
                "min": min(ratios) if ratios else 0,
                "max": max(ratios) if ratios else 0
            }
        
        if "avg_length" in metrics:
            results["avg_length"] = {
                "source": sum(len(t) for t in source_texts) / len(source_texts) if source_texts else 0,
                "target": sum(len(t) for t in translated_texts) / len(translated_texts) if translated_texts else 0
            }
        
        return results


# ==================== 主执行函数 ====================
def main():
    """主入口"""
    print("=" * 60)
    print("Translation Engine Batch Processor")
    print("太玄智译 - 翻译引擎批量处理与质量评估")
    print("=" * 60)
    
    # 加载段落数据
    print("\n[Step 1] Loading paragraph data...")
    paragraphs_file = CONFIG["input_file"]
    paragraphs_file = paragraphs_file.replace("\\ ", "\\")
    
    if not os.path.exists(paragraphs_file):
        # Try alternate path
        paragraphs_file = r"C:\Users\29494\.qclaw\workspace\data_analysis\pdf_ocr_output \paragraphs_full.json"
        paragraphs_file = paragraphs_file.replace(" ", "")
    
    try:
        with open(paragraphs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        paragraphs = data.get("paragraphs", [])
        print(f"[OK] Loaded {len(paragraphs)} paragraphs")
    except FileNotFoundError:
        print(f"[ERROR] File not found: {paragraphs_file}")
        return
    
    # 初始化缓存
    cache = TranslationCache(CONFIG["cache_dir"], CONFIG["cache_enabled"])
    
    # 获取可用引擎（使用项目配置）
    available_engines = []
    for engine_name, engine_config in CONFIG["engines"].items():
        if engine_config.get("enabled", False):
            try:
                translator = TranslatorFactory.create(engine_name, engine_config)
                available_engines.append(engine_name)
                print(f"[OK] Engine available: {engine_name}")
            except Exception as e:
                print(f"[SKIP] Engine not available: {engine_name} - {e}")
    
    # 如果没有可用引擎，启用DeepSeek默认
    if not available_engines:
        print("[WARN] No engines enabled, using DeepSeek as default")
        available_engines = ["deepseek"]
    
    if not available_engines:
        print("\n[ERROR] No translation engines available!")
        print("Please configure at least one engine:")
        print("  - OpenAI: Set OPENAI_API_KEY environment variable")
        print("  - DeepL: Set DEEPL_API_KEY environment variable")
        print("  - Ollama: Start local Ollama server")
        return
    
    # 选择主引擎（优先DeepSeek）
    if "deepseek" in available_engines:
        primary_engine = "deepseek"
    else:
        primary_engine = available_engines[0] if available_engines else "demo"
    print(f"\n[INFO] Primary engine: {primary_engine}")
    
    # 初始化处理器
    processor = BatchTranslationProcessor(
        primary_engine,
        CONFIG["engines"][primary_engine],
        cache
    )
    
    if not processor.enabled:
        print(f"\n[ERROR] Primary engine {primary_engine} not available")
        return
    
    # 执行翻译
    print(f"\n[Step 2] Starting translation with {primary_engine}...")
    print(f"[INFO] Processing {len(paragraphs)} paragraphs...")
    
    def progress_callback(current, total):
        if current % 100 == 0 or current == total:
            print(f"  Progress: {current}/{total}")
    
    result = processor.process_batch(paragraphs, progress_callback)
    
    # 保存结果
    print("\n[Step 3] Saving results...")
    output_dir = Path(CONFIG["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整结果
    output_file = output_dir / f"translations_{primary_engine}_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result.results, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved: {output_file}")
    
    # 保存汇总报告
    summary_file = output_dir / f"translation_summary_{timestamp}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"# Translation Summary Report\n\n")
        f.write(f"**Engine**: {result.engine}\n")
        f.write(f"**Timestamp**: {datetime.now().isoformat()}\n\n")
        f.write(f"## Statistics\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|---------|-------|\n")
        f.write(f"| Total Paragraphs | {result.total_paras} |\n")
        f.write(f"| Success | {result.success_count} |\n")
        f.write(f"| Failed | {result.failed_count} |\n")
        f.write(f"| Success Rate | {result.metrics.get('success_rate', 0):.1%} |\n")
        f.write(f"| Total Time | {result.total_time_seconds:.1f}s |\n")
        f.write(f"| Avg Time/Para | {result.metrics.get('avg_processing_time_ms', 0):.0f}ms |\n")
        f.write(f"| Avg Char Ratio | {result.metrics.get('avg_char_ratio', 0):.2f} |\n")
    print(f"[OK] Saved: {summary_file}")
    
    # 关闭缓存
    cache.close()
    
    print("\n" + "=" * 60)
    print("[OK] Translation completed!")
    print(f"Output: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
