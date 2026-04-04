"""
太玄智译 - 翻译缓存管理
基于 SQLite 实现持久化缓存，支持 TTL 过期清理
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from taixuan_translator.core.config import get_settings
from taixuan_translator.data.database import get_db_session
from taixuan_translator.data.models import TranslationCache


def _make_cache_key(
    source_text: str,
    engine: str,
    source_language: str,
    target_language: str,
    model_name: str = "",
) -> tuple[str, str]:
    """
    生成缓存键和原文哈希。
    
    Returns:
        (cache_key, source_hash)
    """
    source_hash = hashlib.md5(source_text.encode("utf-8")).hexdigest()
    key_raw = f"{source_hash}:{engine}:{source_language}:{target_language}:{model_name}"
    cache_key = hashlib.sha256(key_raw.encode()).hexdigest()
    return cache_key, source_hash


class TranslationCacheManager:
    """翻译缓存管理器"""

    def __init__(self) -> None:
        self.settings = get_settings()

    def get(
        self,
        source_text: str,
        engine: str,
        source_language: str,
        target_language: str,
        model_name: str = "",
    ) -> Optional[str]:
        """
        从缓存获取翻译结果。
        
        Returns:
            译文字符串，未命中返回 None
        """
        if not self.settings.enable_cache:
            return None

        cache_key, _ = _make_cache_key(
            source_text, engine, source_language, target_language, model_name
        )

        try:
            with get_db_session() as session:
                entry = session.query(TranslationCache).filter(
                    TranslationCache.cache_key == cache_key
                ).first()

                if entry is None:
                    return None

                # 检查是否过期
                if entry.expires_at and entry.expires_at < datetime.utcnow():
                    session.delete(entry)
                    logger.debug(f"缓存已过期，已删除: {cache_key[:16]}...")
                    return None

                # 更新命中统计
                entry.hit_count += 1
                entry.last_used_at = datetime.utcnow()

                logger.debug(
                    f"缓存命中 [{engine}] {source_text[:30]}... → {entry.translated_text[:30]}..."
                )
                return entry.translated_text

        except Exception as e:
            logger.warning(f"缓存读取失败（降级为直接翻译）: {e}")
            return None

    def set(
        self,
        source_text: str,
        translated_text: str,
        engine: str,
        source_language: str,
        target_language: str,
        model_name: str = "",
    ) -> bool:
        """
        写入翻译缓存。
        
        Returns:
            是否写入成功
        """
        if not self.settings.enable_cache:
            return False

        cache_key, source_hash = _make_cache_key(
            source_text, engine, source_language, target_language, model_name
        )

        ttl_days = self.settings.cache_ttl_days
        expires_at = datetime.utcnow() + timedelta(days=ttl_days) if ttl_days > 0 else None

        try:
            with get_db_session() as session:
                # 使用 upsert 逻辑
                entry = session.query(TranslationCache).filter(
                    TranslationCache.cache_key == cache_key
                ).first()

                if entry:
                    entry.translated_text = translated_text
                    entry.last_used_at = datetime.utcnow()
                    entry.expires_at = expires_at
                else:
                    entry = TranslationCache(
                        cache_key=cache_key,
                        source_hash=source_hash,
                        source_text=source_text,
                        translated_text=translated_text,
                        engine=engine,
                        source_language=source_language,
                        target_language=target_language,
                        model_name=model_name or None,
                        expires_at=expires_at,
                    )
                    session.add(entry)

            logger.debug(f"缓存写入成功 [{engine}]: {source_text[:30]}...")
            return True

        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
            return False

    def clear_expired(self) -> int:
        """清理过期缓存，返回删除条数"""
        try:
            with get_db_session() as session:
                count = session.query(TranslationCache).filter(
                    TranslationCache.expires_at < datetime.utcnow()
                ).delete(synchronize_session=False)
            logger.info(f"清理过期缓存 {count} 条")
            return count
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0

    def clear_all(self) -> int:
        """清空所有缓存，返回删除条数"""
        try:
            with get_db_session() as session:
                count = session.query(TranslationCache).delete(synchronize_session=False)
            logger.info(f"清空全部缓存 {count} 条")
            return count
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return 0

    def get_stats(self) -> dict[str, object]:
        """获取缓存统计信息"""
        try:
            with get_db_session() as session:
                total = session.query(TranslationCache).count()
                expired = session.query(TranslationCache).filter(
                    TranslationCache.expires_at < datetime.utcnow()
                ).count()
                total_hits = session.query(
                    TranslationCache.hit_count
                ).all()
                hit_sum = sum(h[0] for h in total_hits)

            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "total_hits": hit_sum,
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}


# 全局单例
_cache_manager: Optional[TranslationCacheManager] = None


def get_cache_manager() -> TranslationCacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = TranslationCacheManager()
    return _cache_manager
