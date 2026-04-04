"""
太玄智译 - 引擎管理路由
GET  /api/engines          — 列出全部10个引擎及配置状态
POST /api/engines/test     — 测试指定引擎连通性（真实翻译一句话）
"""
from __future__ import annotations

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

from taixuan_translator.api.schemas import ApiResponse
from taixuan_translator.core.config import get_settings

router = APIRouter(prefix="/api/engines", tags=["引擎管理"])


class EngineInfo(BaseModel):
    name: str
    display_name: str
    configured: bool    # API Key / 服务地址 是否已填写
    available: bool     # 服务是否可连通（Ollama 需实际探测）
    model: str
    note: str = ""
    priority: int = 99  # 推荐优先级（越小越优先）


class EngineTestRequest(BaseModel):
    engine: str
    test_text: str = "Hello, this is a connection test."
    target_language: str = "zh-Hans"


# ─── 引擎元数据（10个）────────────────────────────────────────────────────────

_ENGINE_META: dict[str, dict] = {
    "deepseek": {
        "display_name": "DeepSeek Chat",
        "note": "默认引擎，性价比高，中文理解强",
        "priority": 1,
    },
    "openai": {
        "display_name": "OpenAI (GPT-4o-mini)",
        "note": "翻译质量高，适合高精度需求",
        "priority": 2,
    },
    "qwen": {
        "display_name": "通义千问 (Qwen)",
        "note": "阿里云 DashScope，中文优化",
        "priority": 3,
    },
    "claude": {
        "display_name": "Claude (Anthropic)",
        "note": "长文本理解强，适合学术文献",
        "priority": 4,
    },
    "gemini": {
        "display_name": "Google Gemini",
        "note": "多语言支持广泛",
        "priority": 5,
    },
    "minimax": {
        "display_name": "MiniMax",
        "note": "国产大模型，中文表现优秀",
        "priority": 6,
    },
    "grok": {
        "display_name": "Grok (xAI)",
        "note": "xAI 出品，实时信息能力强",
        "priority": 7,
    },
    "deepl": {
        "display_name": "DeepL",
        "note": "专业翻译引擎，欧洲语言最佳",
        "priority": 8,
    },
    "ollama": {
        "display_name": "Ollama (本地模型)",
        "note": "完全离线，数据不出本机",
        "priority": 9,
    },
    "custom": {
        "display_name": "自定义引擎",
        "note": "出版集团自建模型 / 私有部署",
        "priority": 10,
    },
}


def _get_engine_model(settings, name: str) -> str:
    """安全获取引擎模型名"""
    try:
        cfg = getattr(settings, name, None)
        return cfg.model if cfg and hasattr(cfg, "model") else "—"
    except Exception:
        return "—"


def _is_configured(settings, name: str) -> bool:
    """判断引擎是否已配置"""
    if name == "ollama":
        return True  # Ollama 无需 API Key
    if name == "custom":
        cfg = getattr(settings, "custom", None)
        return bool(cfg and cfg.base_url and cfg.model)
    cfg = getattr(settings, name, None)
    return bool(cfg and getattr(cfg, "api_key", ""))


@router.get("", response_model=ApiResponse)
async def list_engines() -> ApiResponse:
    """
    列出全部10个翻译引擎及其配置状态。
    
    **前端使用建议：**
    - `configured=true` 且 `available=true` → 可直接使用
    - `configured=false` → 引导用户填写 API Key
    - `available=false`（仅 Ollama）→ 提示启动本地服务
    
    **返回示例：**
    ```json
    {
      "engines": [
        {"name": "deepseek", "configured": true, "available": true, "priority": 1},
        {"name": "ollama",   "configured": true, "available": false, "priority": 9}
      ],
      "default_engine": "deepseek",
      "configured_count": 1
    }
    ```
    """
    settings = get_settings()
    engines: list[EngineInfo] = []

    # Ollama 需异步探测
    ollama_alive = await _check_ollama(settings.ollama.base_url)

    for name, meta in _ENGINE_META.items():
        configured = _is_configured(settings, name)
        if name == "ollama":
            available = ollama_alive
        else:
            available = configured  # 有 Key 即视为可用（实际连通性在 /test 验证）

        note = meta["note"]
        if name == "ollama" and not ollama_alive:
            note += " — 服务未启动，请运行: ollama serve"

        engines.append(EngineInfo(
            name=name,
            display_name=meta["display_name"],
            configured=configured,
            available=available,
            model=_get_engine_model(settings, name),
            note=note,
            priority=meta["priority"],
        ))

    # 按优先级排序
    engines.sort(key=lambda e: e.priority)
    configured_count = sum(1 for e in engines if e.available)

    return ApiResponse.ok(
        data={
            "engines": [e.model_dump() for e in engines],
            "default_engine": str(settings.default_engine.value
                                  if hasattr(settings.default_engine, "value")
                                  else settings.default_engine),
            "configured_count": configured_count,
            "total_count": len(engines),
        },
        message=f"共{len(engines)}个引擎，{configured_count}个可用"
    )


@router.post("/test", response_model=ApiResponse)
async def test_engine(request: EngineTestRequest) -> ApiResponse:
    """
    测试指定引擎连通性（发送真实翻译请求验证）。
    
    **前端使用：** 设置页面"测试连接"按钮
    
    **注意：** 会消耗少量 API Token（约10-20个）
    """
    logger.info(f"[EngineTest] 测试引擎: {request.engine}")

    try:
        from taixuan_translator.translator.factory import TranslationEngineFactory

        # 验证引擎名合法
        valid_engines = TranslationEngineFactory.list_all_engines()
        if request.engine not in valid_engines:
            return ApiResponse.error(
                f"未知引擎: {request.engine}，可用引擎: {valid_engines}",
                code=400
            )

        engine = TranslationEngineFactory.get_engine(request.engine)

        if not engine.validate_config():
            return ApiResponse.error(
                f"引擎 [{request.engine}] 未配置，请先在 .env 中填写对应 API Key",
                code=503
            )

        result = engine.translate(
            text=request.test_text,
            source_language="en",
            target_language=request.target_language,
        )

        if result.success:
            logger.info(f"[EngineTest] {request.engine} 测试通过")
            return ApiResponse.ok(
                data={
                    "engine": request.engine,
                    "model": result.model_name,
                    "source": result.source_text,
                    "translated": result.translated_text,
                    "from_cache": result.from_cache,
                    "tokens_used": result.tokens_used,
                },
                message=f"引擎 [{request.engine}] 连接正常"
            )
        else:
            return ApiResponse.error(
                f"翻译测试失败: {result.error}",
                code=503
            )

    except ValueError as e:
        return ApiResponse.error(str(e), code=400)
    except Exception as e:
        logger.error(f"[EngineTest] {request.engine} 测试异常: {e}")
        return ApiResponse.error(str(e), code=503)


async def _check_ollama(base_url: str) -> bool:
    """异步探测 Ollama 服务是否在线（3秒超时）"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
