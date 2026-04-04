"""
太玄智译 - API 服务独立启动入口
PyInstaller 打包专用入口点
用法: taixuan-translator-api.exe [--host HOST] [--port PORT]
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="太玄智译 API 服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="监听端口 (默认: 8000)")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数 (默认: 1)")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载 (打包版不支持)")
    args = parser.parse_args()

    # PyInstaller 打包后资源路径修正
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
        sys.path.insert(0, str(base_path))

    import uvicorn
    from taixuan_translator.core.utils import setup_logging
    from taixuan_translator.data.database import init_database

    setup_logging()
    init_database()

    print(f"[太玄智译] API 服务启动中... http://{args.host}:{args.port}")
    print(f"[太玄智译] API 文档: http://{args.host}:{args.port}/docs")
    print("[太玄智译] 按 Ctrl+C 停止服务")

    uvicorn.run(
        "taixuan_translator.api.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers if not getattr(sys, 'frozen', False) else 1,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
