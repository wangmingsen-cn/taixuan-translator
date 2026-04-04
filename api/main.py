"""
太玄智译 - FastAPI Web服务主入口
启动命令: uvicorn taixuan_translator.api.main:app --reload --port 8000
或: python -m taixuan_translator.api.main
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request  # type: ignore[import]
from fastapi.middleware.cors import CORSMiddleware  # type: ignore[import]
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse  # type: ignore[import]
from fastapi.staticfiles import StaticFiles  # type: ignore[import]
from loguru import logger

from taixuan_translator.api import ApiResponse
from taixuan_translator.api.routers import upload_router, export_router, status_router, translate_router, engines_router
from taixuan_translator.core.config import get_settings
from taixuan_translator.core.utils import setup_logging


# ─── 生命周期管理 ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    # 启动
    setup_logging()
    from taixuan_translator.data.database import init_database
    init_database()
    logger.info("太玄智译 API 服务已启动")
    yield
    # 关闭
    logger.info("太玄智译 API 服务已关闭")


# ─── FastAPI 应用实例 ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="太玄智译 API",
        description="""
## 太玄智译 - PDF精准翻译工具

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/upload` | 上传文件 | 解析PDF/Word/ePub等格式，返回段落列表 |
| `POST /api/translate` | 翻译段落 | 调用OpenAI/DeepL/Ollama引擎翻译 |
| `POST /api/export/docx` | 导出Word | 生成出版级Word文档 |
| `GET /api/status/{task_id}` | 查询进度 | 轮询任务执行状态 |
| `GET /api/downloads/{filename}` | 下载文件 | 下载已导出的文档 |

### 前端对接说明

```javascript
// 1. 上传文件
const formData = new FormData();
formData.append('file', fileInput.files[0]);
const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
const { task_id, segments } = uploadRes.data;

// 2. 翻译（批量）
const translateRes = await fetch('/api/translate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    task_id,
    segments: segments.map(s => ({ index: s.index, text: s.text })),
    engine: 'openai',
    target_language: 'zh-Hans'
  })
});

// 3. 导出Word
const exportRes = await fetch('/api/export/docx', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    file_name: 'paper.pdf',
    segments: translateResults,
    bilingual_mode: 'interleaved'
  })
});

// 4. 下载
window.location.href = exportRes.data.download_url;
```
""",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ─── 中间件配置 ───────────────────────────────────────────────────────

    # CORS：允许前端访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # 开发环境允许所有，生产环境建议限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        import time
        start = time.time()
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        logger.debug(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.0f}ms)")
        return response

    # ─── 全局异常处理 ─────────────────────────────────────────────────────

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"未处理异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "code": 500, "message": f"服务器内部错误: {str(exc)}", "data": None}
        )

    # ─── 注册路由 ─────────────────────────────────────────────────────────

    app.include_router(upload_router)
    app.include_router(translate_router)
    app.include_router(export_router)
    app.include_router(status_router)
    app.include_router(engines_router)

    # ─── 健康检查 ─────────────────────────────────────────────────────────

    @app.get("/health", tags=["系统"])
    async def health_check() -> ApiResponse:
        """服务健康检查（前端轮询探测）"""
        from taixuan_translator.data.database import check_database_health
        db_status = check_database_health()
        return ApiResponse.ok(
            data={"service": "ok", "database": db_status},
            message="太玄智译服务运行正常"
        )

    # ─── 静态文件服务（Web UI）──────────────────────────────
    
    # 确定 Web UI 目录
    ui_web_paths = [
        Path(__file__).parent.parent / "ui" / "web",
        Path(__file__).parent.parent.parent / "taixuan_translator" / "ui" / "web",
    ]
    ui_web_dir = None
    for p in ui_web_paths:
        if p.exists():
            ui_web_dir = p
            break
    
    if ui_web_dir and ui_web_dir.is_dir():
        # 挂载静态文件目录
        app.mount("/static", StaticFiles(directory=str(ui_web_dir)), name="web")
        logger.info(f"静态文件目录: {ui_web_dir}")
    
    @app.get("/", tags=["系统"])
    async def root():
        """根路径 - 返回主界面"""
        if ui_web_dir:
            index_path = ui_web_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
        
        # 如果找不到，返回欢迎页面
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>太玄智译</title>
            <style>
                body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #1a1a2e; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .container { text-align: center; padding: 40px; background: #16213e; border-radius: 16px; }
                h1 { color: #e94560; margin-bottom: 20px; }
                p { color: #a0a0a0; }
                a { color: #4a9eff; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>太玄智译 v1.0</h1>
                <p>PDF 精准翻译解决方案</p>
                <p>太玄计算机软件开发工作室</p>
                <hr style="border-color: #333; margin: 30px 0;">
                <p><a href="/docs">📖 API 文档</a></p>
                <p><a href="/health">🔧 健康检查</a></p>
            </div>
        </body>
        </html>
        """, status_code=200)

    return app


# ─── 应用实例 ────────────────────────────────────────────────────────────────

app = create_app()


# ─── 直接运行入口 ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "taixuan_translator.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
