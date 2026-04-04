# -*- coding: utf-8 -*-
"""
太玄智译 - 静默启动入口
双击 exe → 后台启动 API 服务 → 自动打开浏览器
无弹窗、无控制台
"""
import sys
import os
import time
import socket
import threading
import webbrowser

PORT = 8000
URL = "http://127.0.0.1:%d" % PORT


def check_port(port):
    """检查端口是否已在监听"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def run_server():
    """在后台线程中启动 FastAPI 服务"""
    import uvicorn
    uvicorn.run(
        "taixuan_translator.api.main:app",
        host="127.0.0.1",
        port=PORT,
        log_level="info",
    )


def main():
    # 如果服务已在运行，直接打开浏览器
    if check_port(PORT):
        webbrowser.open(URL)
        return

    # 后台启动 API 服务
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 等待服务就绪（最多 30 秒）
    for _ in range(30):
        time.sleep(1)
        if check_port(PORT):
            break

    # 自动打开浏览器
    webbrowser.open(URL)

    # 主线程保持运行（阻塞直到进程被终止）
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
