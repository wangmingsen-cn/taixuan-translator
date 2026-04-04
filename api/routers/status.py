"""
太玄智译 - 任务状态查询接口
GET /api/status/{task_id}
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path
from loguru import logger

from taixuan_translator.api.schemas import ApiResponse, TaskStatusResponse, TaskStatusEnum
from taixuan_translator.core.exceptions import RecordNotFoundError
from taixuan_translator.data.database import get_db_session
from taixuan_translator.data.models import TranslationTask, TaskStatus

router = APIRouter(prefix="/api", tags=["任务管理"])


@router.get("/status/{task_id}", response_model=ApiResponse)
async def get_task_status(
    task_id: int = Path(..., description="任务ID", ge=1),
) -> ApiResponse:
    """
    查询翻译/解析任务状态。
    
    **前端轮询间隔建议：** 每2秒查询一次，进度>90%时停止
    
    **返回示例：**
    ```json
    {
      "success": true,
      "data": {
        "task_id": 42,
        "status": "translating",
        "progress": 45,
        "current_step": "正在翻译第23/52段...",
        "total_segments": 52,
        "translated_segments": 23
      }
    }
    ```
    """
    try:
        with get_db_session() as session:
            task = session.query(TranslationTask).filter(
                TranslationTask.id == task_id
            ).first()

            if not task:
                return ApiResponse.error(f"任务不存在（ID: {task_id}）", code=404)

            # 计算进度
            progress = task.progress
            if task.total_segments > 0 and progress == 0:
                progress = int(task.translated_chars / max(task.total_chars, 1) * 100)

            # 映射状态
            status_map = {
                TaskStatus.PENDING: TaskStatusEnum.PENDING,
                TaskStatus.RUNNING: TaskStatusEnum.TRANSLATING,
                TaskStatus.COMPLETED: TaskStatusEnum.COMPLETED,
                TaskStatus.FAILED: TaskStatusEnum.FAILED,
                TaskStatus.CANCELLED: TaskStatusEnum.CANCELLED,
                TaskStatus.PAUSED: TaskStatusEnum.PAUSED,
            }
            status = status_map.get(task.status, TaskStatusEnum.PENDING)

            # 步骤描述
            step_map = {
                TaskStatusEnum.PENDING: "等待处理...",
                TaskStatusEnum.PARSING: "正在解析文档...",
                TaskStatusEnum.TRANSLATING: f"正在翻译...（{task.translated_chars}/{task.total_chars}字符）",
                TaskStatusEnum.GENERATING: "正在生成文档...",
                TaskStatusEnum.COMPLETED: "已完成",
                TaskStatusEnum.FAILED: f"失败: {task.error_message or '未知错误'}",
            }

            # 时间格式化
            def fmt(dt): return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

            response = TaskStatusResponse(
                task_id=task.id,
                status=status,
                progress=min(progress, 100),
                current_step=step_map.get(status, ""),
                total_segments=task.total_segments,
                translated_segments=task.processed_pages,
                error_message=task.error_message,
                created_at=fmt(task.created_at),
                started_at=fmt(task.started_at),
                completed_at=fmt(task.completed_at),
                duration_seconds=task.duration_seconds,
            )

            return ApiResponse.ok(data=response.model_dump(mode="json"))

    except Exception as e:
        logger.exception(f"[Status] 查询失败 task_id={task_id}: {e}")
        return ApiResponse.error(f"服务器内部错误", code=500)
