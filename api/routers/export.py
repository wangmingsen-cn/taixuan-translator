"""
太玄智译 - 导出接口路由
POST /api/export/docx
GET /api/downloads/{filename}
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query, Response  # type: ignore[import]
from fastapi.responses import FileResponse  # type: ignore[import]
from loguru import logger

from taixuan_translator.api.schemas import (
    ApiResponse,
    BilingualModeEnum,
    ExportDocxRequest,
    ExportDocxResponse,
    ExportSegment,
)
from taixuan_translator.core.config import get_settings
from taixuan_translator.services.export_service import ExportService

router = APIRouter(prefix="/api", tags=["文档导出"])


@router.post("/export/docx", response_model=ApiResponse)
async def export_docx(request: ExportDocxRequest) -> ApiResponse:
    """
    导出 Word 文档（出版级 GB/T 标准）。
    
    **前置条件：**
    - 前端已调用 POST /api/upload 获取段落
    - 用户已完成所有段落翻译（或部分翻译）
    - 前端将翻译结果通过此接口提交
    
    **请求示例：**
    ```json
    {
      "file_name": "paper.pdf",
      "segments": [
        {
          "index": 0,
          "source_text": "Deep Learning Survey",
          "translated_text": "深度学习综述",
          "type": "title",
          "page": 1
        },
        {
          "index": 1,
          "source_text": "In recent years...",
          "translated_text": "近年来，...",
          "type": "text",
          "page": 1
        }
      ],
      "bilingual_mode": "interleaved",
      "source_language": "en",
      "target_language": "zh-Hans",
      "apply_publication_std": true
    }
    ```
    """
    try:
        if not request.segments:
            return ApiResponse.error("翻译段落列表为空，请先翻译文档", code=400)

        service = ExportService()
        result = service.export_docx(request)

        logger.info(
            f"[Export] Word导出成功: {result.file_name}, "
            f"{result.total_segments}段落, {result.file_size_kb}KB"
        )

        return ApiResponse.ok(
            data=result.model_dump(mode="json"),
            message=f"文档导出成功，共{result.total_segments}段"
        )

    except Exception as e:
        logger.exception(f"[Export] Word导出失败: {e}")
        return ApiResponse.error(f"导出失败: {str(e)}", code=500)


@router.get("/downloads/{filename}")
async def download_file(
    filename: str = Path(description="文件名"),
) -> Response:
    """
    下载已导出的文件。
    
    **前端使用：**
    ```javascript
    const link = document.createElement('a');
    link.href = `/api/downloads/${encodeURIComponent(fileName)}`;
    link.download = fileName;
    link.click();
    ```
    """
    settings = get_settings()
    export_dir = settings.app_dir / "exports"
    file_path = export_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    # 安全检查：防止路径遍历
    if not str(file_path).startswith(str(export_dir.resolve())):
        raise HTTPException(status_code=403, detail="非法请求")

    suffix = file_path.suffix.lower()
    media_map = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain; charset=utf-8",
        ".html": "text/html; charset=utf-8",
    }
    media_type = media_map.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )
