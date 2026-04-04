"""
太玄智译 - 上传接口路由
POST /api/upload
"""
from __future__ import annotations

import io
import time
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile  # type: ignore[import]
from loguru import logger

from taixuan_translator.api.schemas import ApiResponse, UploadResponse
from taixuan_translator.core.exceptions import (
    FileOperationError,
    FileTooLargeError,
    TaixuanBaseError,
    UnsupportedFileTypeError,
)
from taixuan_translator.services.file_parser import FileParseService

router = APIRouter(prefix="/api", tags=["文件处理"])


@router.post("/upload", response_model=ApiResponse)
async def upload_file(
    file: Annotated[UploadFile, File(description="要翻译的文件（PDF/Word/ePub/HTML/TXT/SRT）")],
) -> ApiResponse:
    """
    上传文件并解析为段落结构。
    
    **功能：**
    - 接收前端上传的文件流
    - 校验文件类型和大小（≤500MB）
    - 根据文件类型调用对应解析器
    - 返回段落列表（含页码、类型、原文）
    
    **前端对接：**
    - `Content-Type: multipart/form-data`
    - `form-data key: file`
    
    **返回示例：**
    ```json
    {
      "success": true,
      "data": {
        "task_id": 42,
        "file_name": "paper.pdf",
        "file_type": "pdf",
        "total_segments": 156,
        "segments": [
          {"index": 0, "page": 1, "type": "title", "text": "Deep Learning Survey"},
          {"index": 1, "page": 1, "type": "text", "text": "In recent years..."}
        ],
        "parse_duration_ms": 2341
      }
    }
    ```
    """
    try:
        # 读取文件内容到内存
        content = await file.read()
        file_stream = io.BytesIO(content)

        # 解析
        service = FileParseService()
        result = service.parse_upload(
            file_stream=file_stream,
            file_name=file.filename or "unknown",
            file_size=len(content),
        )

        return ApiResponse.ok(
            data=result.model_dump(mode="json"),
            message=f"文件解析成功，共{result.total_segments}个段落"
        )

    except UnsupportedFileTypeError as e:
        logger.warning(f"[Upload] 不支持的文件类型: {file.filename}: {e}")
        return ApiResponse.error(str(e), code=415)

    except FileTooLargeError as e:
        logger.warning(f"[Upload] 文件过大: {file.filename}: {e}")
        return ApiResponse.error(str(e), code=413)

    except TaixuanBaseError as e:
        logger.error(f"[Upload] 业务异常: {e}")
        return ApiResponse.error(str(e), code=400)

    except Exception as e:
        logger.exception(f"[Upload] 未知错误: {e}")
        return ApiResponse.error(f"服务器内部错误: {str(e)}", code=500)
