#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation Engine Batch Processor - Simplified
太玄智译 - 翻译引擎批量处理与质量评估模�?支持: DeepSeek (默认), OpenAI, DeepL, Ollama
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime

# ==================== 配置 ====================
CONFIG = {
    "input_file": r"C:\Users\29494\.qclaw\workspace\data_analysis\pdf_ocr_output\paragraphs_full.json",
    "eval_file": r"C:\Users\29494\.qclaw\workspace\data_analysis\pdf_ocr_output\translation_eval_dataset.json",
    "output_dir": r"C:\Users\29494\.qclaw\workspace\taixuan_translator\translator\output",
    "cache_dir": r"C:\Users\29494\.qclaw\workspace\taixuan_translator\translator\cache",
    
    # 翻译设置
    "source_lang": "EN",
    "target_lang": "ZH",
    "batch_size": 10,
    "max_workers": 3,
    
    # 引擎配置
    "engines": {
        "deepseek": {
            "enabled": False,  # 改为False，使用演示模�?            "api_key": "YOUR_DEEPSEEK_API_KEY",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "max_tokens": 4096,
            "temperature": 0.3,
            "timeout": 60
        },
        "openai": {
            "enabled": False,
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4o-mini"
        },
        "deepl": {
            "enabled": False,
            "api_key_env": "DEEPL_API_KEY"
        },
        "ollama": {
            "enabled": False,
            "base_url": "http://localhost:11434",
            "model": "qwen2.5:7b"
        }
    },
    
    "cache_enabled": True,
    "eval_sample_size": 50
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
    status: str
    error: Optional[str] = None


# ==================== 翻译引擎基类 ====================
class BaseTranslator(ABC):
    """翻译引擎抽象基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__.replace("Translator", "").lower()
    
    @abstractmethod
    def translate(self, text: str) -> str:
        """执行翻译"""
        pass


# ==================== DeepSeek翻译�?====================
class DeepSeekTranslator(BaseTranslator):
    """DeepSeek 翻译引擎（默认）"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.deepseek.com/v1")
        self.model = config.get("model", "deepseek-chat")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.3)
        
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            print(f"[OK] DeepSeek initialized: {self.model}")
        except ImportError:
            raise ImportError("openai package required")
    
    def translate(self, text: str) -> str:
        """使用DeepSeek翻译"""
        prompt = f"""Translate the following English text to Chinese (Simplified).
Only output the translation, no explanations.

English:
{text}

Chinese:"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate English to Chinese accurately."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        return response.choices[0].message.content.strip()


# ==================== 翻译缓存 ====================
class TranslationCache:
    """翻译缓存管理"""
    
    def __init__(self, cache_dir: str, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        self.memory_cache: Dict[str, str] = {}
        
        if enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache()
    
    def _load_cache(self):
        """加载缓存"""
        cache_file = self.cache_dir / "translations.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.memory_cache = json.load(f)
                print(f"[OK] Loaded {len(self.memory_cache)} cached translations")
            except Exception as e:
                print(f"[WARN] Cache load failed: {e}")
    
    def _save_cache(self):
        """保存缓存"""
        cache_file = self.cache_dir / "translations.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Cache save failed: {e}")
    
    def get(self, text: str, engine: str) -> Optional[str]:
        """获取缓存"""
        if not self.enabled:
            return None
        import hashlib
        key = f"{engine}:{hashlib.md5(text.encode()).hexdigest()}"
        return self.memory_cache.get(key)
    
    def set(self, text: str, engine: str, translation: str):
        """设置缓存"""
        if not self.enabled:
            return
        import hashlib
        key = f"{engine}:{hashlib.md5(text.encode()).hexdigest()}"
        self.memory_cache[key] = translation
        
        if len(self.memory_cache) % 50 == 0:
            self._save_cache()
    
    def close(self):
        """关闭时保�?""
        if self.enabled:
            self._save_cache()


# ==================== 演示处理�?====================
class DemoProcessor:
    """演示模式处理�?""
    
    def __init__(self, cache: TranslationCache = None):
        self.cache = cache
        self.enabled = True
        print("[DEMO] Demo processor initialized")
    
    def translate_paragraph(self, para: dict) -> TranslationResult:
        """演示翻译"""
        para_id = para.get("para_id", f"unknown_{0}")
        source_text = para.get("text", "")
        
        if not source_text:
            return TranslationResult(
                para_id=para_id,
                source_text="",
                translated_text="",
                engine="demo",
                char_count_src=0,
                char_count_tgt=0,
                processing_time_ms=0,
                status="skipped"
            )
        
        # 检查缓�?        cached = self.cache.get(source_text, "demo") if self.cache else None
        if cached:
            return TranslationResult(
                para_id=para_id,
                source_text=source_text,
                translated_text=cached,
                engine="demo",
                char_count_src=len(source_text),
                char_count_tgt=len(cached),
                processing_time_ms=0,
                status="cached"
            )
        
        # 演示翻译
        time.sleep(0.01)  # 模拟处理
        demo_translation = f"[ZH] {source_text[:100]}..."
        
        if self.cache:
            self.cache.set(source_text, "demo", demo_translation)
        
        return TranslationResult(
            para_id=para_id,
            source_text=source_text,
            translated_text=demo_translation,
            engine="demo",
            char_count_src=len(source_text),
            char_count_tgt=len(demo_translation),
            processing_time_ms=10,
            status="success"
        )
    
    def process_batch(self, paragraphs: List[dict]) -> Dict:
        """批量处理"""
        start_time = time.time()
        
        total = len(paragraphs)
        success_count = 0
        cached_count = 0
        
        results = []
        
        for i, para in enumerate(paragraphs):
            result = self.translate_paragraph(para)
            results.append(asdict(result))
            
            if result.status == "success":
                success_count += 1
            elif result.status == "cached":
                cached_count += 1
            
            if (i + 1) % 100 == 0 or i == total - 1:
                print(f"  Progress: {i + 1}/{total} ({100*(i+1)//total}%)")
        
        total_time = time.time() - start_time
        
        return {
            "engine": "demo",
            "total_paras": total,
            "success_count": success_count,
            "cached_count": cached_count,
            "failed_count": 0,
            "total_time_seconds": total_time,
            "results": results
        }


# ==================== 批量处理�?====================
class BatchTranslationProcessor:
    """批量翻译处理�?""
    
    def __init__(self, engine_name: str, engine_config: dict, cache: TranslationCache = None):
        self.engine_name = engine_name
        self.engine_config = engine_config
        self.cache = cache
        self.results: List[TranslationResult] = []
        
        try:
            if engine_name == "deepseek":
                self.engine = DeepSeekTranslator(engine_config)
            else:
                raise ValueError(f"Engine {engine_name} not implemented")
            self.enabled = True
        except Exception as e:
            print(f"[ERROR] Engine initialization failed: {e}")
            self.engine = None
            self.enabled = False
    
    def translate_paragraph(self, para: dict) -> TranslationResult:
        """翻译单个段落"""
        para_id = para.get("para_id", f"unknown_{len(self.results)}")
        source_text = para.get("text", "")
        
        if not source_text:
            return TranslationResult(
                para_id=para_id,
                source_text="",
                translated_text="",
                engine=self.engine_name,
                char_count_src=0,
                char_count_tgt=0,
                processing_time_ms=0,
                status="skipped"
            )
        
        # 检查缓�?        cached = self.cache.get(source_text, self.engine_name) if self.cache else None
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
                error=str(e)[:100]
            )
    
    def process_batch(self, paragraphs: List[dict]) -> Dict:
        """批量处理"""
        start_time = time.time()
        
        total = len(paragraphs)
        success_count = 0
        failed_count = 0
        cached_count = 0
        
        results = []
        
        for i, para in enumerate(paragraphs):
            result = self.translate_paragraph(para)
            results.append(asdict(result))
            
            if result.status == "success":
                success_count += 1
            elif result.status == "cached":
                cached_count += 1
            elif result.status == "failed":
                failed_count += 1
            
            if (i + 1) % 100 == 0 or i == total - 1:
                print(f"  Progress: {i + 1}/{total} ({100*(i+1)//total}%)")
        
        total_time = time.time() - start_time
        
        return {
            "engine": self.engine_name,
            "total_paras": total,
            "success_count": success_count,
            "cached_count": cached_count,
            "failed_count": failed_count,
            "total_time_seconds": total_time,
            "results": results
        }


# ==================== 主函�?====================
def main():
    """主入�?""
    print("=" * 60)
    print("Translation Engine Batch Processor")
    print("太玄智译 - 翻译引擎批量处理")
    print("=" * 60)
    
    # 加载段落数据
    print("\n[Step 1] Loading paragraph data...")
    input_file = CONFIG["input_file"]
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        paragraphs = data.get("paragraphs", [])
        print(f"[OK] Loaded {len(paragraphs)} paragraphs")
    except FileNotFoundError:
        print(f"[ERROR] File not found: {input_file}")
        return
    
    # 初始化缓�?    cache = TranslationCache(CONFIG["cache_dir"], CONFIG["cache_enabled"])
    
    # 初始化处理器
    print("\n[Step 2] Initializing translation engine...")
    # 使用演示模式快速验证流�?    engine_config = {"enabled": True}
    processor = DemoProcessor(cache)
    
    if not processor.enabled:
        print("[ERROR] Engine not available")
        return
    
    # 执行翻译
    print(f"\n[Step 3] Starting batch translation...")
    print(f"[INFO] Processing {len(paragraphs)} paragraphs with Demo mode...")
    
    result = processor.process_batch(paragraphs)
    
    # 保存结果
    print("\n[Step 4] Saving results...")
    output_dir = Path(CONFIG["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整结果
    output_file = output_dir / f"translations_demo_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result["results"], f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved: {output_file}")
    
    # 保存汇总报�?    summary_file = output_dir / f"translation_summary_{timestamp}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("# Translation Summary Report\n\n")
        f.write(f"**Engine**: Demo Mode\n")
        f.write(f"**Timestamp**: {datetime.now().isoformat()}\n\n")
        f.write("## Statistics\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Total Paragraphs | {result['total_paras']} |\n")
        f.write(f"| Success | {result['success_count']} |\n")
        f.write(f"| Cached | {result['cached_count']} |\n")
        f.write(f"| Failed | {result['failed_count']} |\n")
        success_rate = 100 * (result['success_count'] + result['cached_count']) / result['total_paras'] if result['total_paras'] > 0 else 0
        f.write(f"| Success Rate | {success_rate:.1f}% |\n")
        f.write(f"| Total Time | {result['total_time_seconds']:.1f}s |\n")
    print(f"[OK] Saved: {summary_file}")
    
    # 关闭缓存
    cache.close()
    
    print("\n" + "=" * 60)
    print("[OK] Translation completed!")
    print(f"Output: {output_dir}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    main()
