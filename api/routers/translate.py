"""
太玄智译 - 翻译接口路由
POST /api/translate
"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from taixuan_translator.api.schemas import (
    ApiResponse,
    TranslateRequest,
    TranslateResponse,
)
from taixuan_translator.core.exceptions import (
    InvalidAPIKeyError,
    OllamaNotRunningError,
    TaixuanBaseError,
    TranslationAPIError,
    TranslationRateLimitError,
    TranslationTimeoutError,
)
from taixuan_translator.translator.factory import TranslationEngineFactory

router = APIRouter(prefix="/api", tags=["翻译引擎"])


@router.post("/translate", response_model=ApiResponse)
async def translate_segments(request: TranslateRequest) -> ApiResponse:
    """
    翻译段落（支持单条/批量，自动处理缓存）。
    
    **引擎选择：**
    - `openai` — GPT-4o-mini（需配置 API Key）
    - `deepl` — DeepL（需配置 API Key）
    - `ollama` — 本地模型（需启动 Ollama 服务）
    - `deepseek` — DeepSeek（需配置 API Key）
    
    **请求示例：**
    ```json
    {
      "segments": [
        {"index": 0, "text": "Deep Learning Survey"},
        {"index": 1, "text": "In recent years, deep learning has revolutionized..."}
      ],
      "engine": "openai",
      "source_language": "en",
      "target_language": "zh-Hans"
    }
    ```
    
    **响应示例：**
    ```json
    {
      "success": true,
      "data": {
        "task_id": 42,
        "results": [
          {"index": 0, "source": "Deep Learning Survey", "translated": "深度学习综述", "from_cache": false},
          {"index": 1, "source": "In recent years...", "translated": "近年来...", "from_cache": true}
        ],
        "total_tokens": 2341,
        "cache_hits": 1,
        "duration_ms": 4521
      }
    }
    ```
    """
    start_time = time.time()

    try:
        # 获取翻译引擎
        engine = TranslationEngineFactory.get_engine(request.engine)

        # 验证配置
        if not engine.validate_config():
            return ApiResponse.error(
                f"翻译引擎 {request.engine} 未配置，请先在设置中填写 API Key",
                code=503,
            )

        # 批量翻译
        texts = [seg.get("text", "") for seg in request.segments]
        results = engine.translate_batch(
            texts=texts,
            source_language=request.source_language,
            target_language=request.target_language,
        )

        # 整理返回
        response_results = []
        for i, seg in enumerate(request.segments):
            r = results.results[i] if i < len(results.results) else None
            response_results.append({
                "index": seg.get("index", i),
                "source": seg.get("text", ""),
                "translated": r.translated_text if r else "",
                "from_cache": r.from_cache if r else False,
                "error": r.error if r and not r.success else None,
            })

        elapsed_ms = int((time.time() - start_time) * 1000)

        response = TranslateResponse(
            task_id=request.task_id,
            results=response_results,
            total_tokens=results.total_tokens,
            cache_hits=results.cache_hits,
            duration_ms=elapsed_ms,
        )

        logger.info(
            f"[Translate] {request.engine}: {len(texts)}段, "
            f"{results.cache_hits}缓存命中, {elapsed_ms}ms"
        )

        return ApiResponse.ok(data=response.model_dump(mode="json"))

    except InvalidAPIKeyError as e:
        logger.warning(f"[Translate] API Key无效: {e}")
        return ApiResponse.error(str(e), code=401)

    except TranslationRateLimitError as e:
        logger.warning(f"[Translate] 限流: {e}")
        return ApiResponse.error(str(e), code=429)

    except TranslationTimeoutError as e:
        logger.warning(f"[Translate] 超时: {e}")
        return ApiResponse.error(str(e), code=504)

    except OllamaNotRunningError:
        logger.warning("[Translate] Ollama服务未启动")
        return ApiResponse.error(
            "Ollama本地服务未启动，请先运行: ollama serve",
            code=503,
        )

    except TaixuanBaseError as e:
        logger.error(f"[Translate] 翻译异常: {e}")
        return ApiResponse.error(str(e), code=500)

    except Exception as e:
        logger.exception(f"[Translate] 未知错误: {e}")
        return ApiResponse.error(f"服务器内部错误: {str(e)}", code=500)
