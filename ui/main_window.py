# -*- coding: utf-8 -*-
"""
太玄智译 - 桌面启动器
功能：自动启动 API 服务，打开浏览器，无需用户手动操作
"""

import sys
import os
import subprocess
import time
import socket
import webbrowser
import ctypes
from pathlib import Path

# 日志目录
LOG_DIR = Path.home() / ".taixuan_translator" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "launcher.log"

def log(msg):
    """写入日志"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")

def check_port(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_api_exe():
    """查找 API 服务 EXE"""
    if getattr(sys, 'frozen', False):
        app_dir = Path(sys.executable).parent
    else:
        # 开发模式：从源码运行
        return None
    
    # 优先查找当前目录
    api_exe = app_dir / "taixuan-translator-api.exe"
    if api_exe.exists():
        return api_exe
    
    # 查找 _internal 目录
    api_exe = app_dir / "_internal" / "taixuan-translator-api.exe"
    if api_exe.exists():
        return api_exe
    
    return None

def is_admin():
    """检查是否管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    """主函数"""
    log("=" * 50)
    log("太玄智译 v1.0 启动器")
    log("=" * 50)
    
    PORT = 8000
    URL = f"http://127.0.0.1:{PORT}"
    
    # 检查端口
    if check_port(PORT):
        log(f"检测到端口 {PORT} 已被占用，服务可能已在运行")
        log(f"直接打开浏览器: {URL}")
        webbrowser.open(URL)
        input("\n按回车键退出...")
        return
    
    # 查找 API EXE
    api_exe = find_api_exe()
    
    if api_exe:
        log(f"找到 API 服务: {api_exe}")
    else:
        log("未找到 API 服务 EXE，尝试从源码启动...")
        # 从源码启动（开发模式）
        src_dir = Path(__file__).parent.parent.parent
        api_exe = sys.executable  # 使用当前 Python 解释器
    
    # 启动 API 服务
    log(f"启动 API 服务 (端口 {PORT})...")
    
    try:
        if api_exe and str(api_exe).endswith(".exe"):
            # 使用打包的 EXE
            proc = subprocess.Popen(
                [str(api_exe), "--host", "127.0.0.1", "--port", str(PORT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(Path(api_exe).parent)
            )
            log(f"进程已启动 (PID: {proc.pid})")
        else:
            # 从源码启动
            src_dir = Path(__file__).parent.parent.parent
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn",
                 "taixuan_translator.api.main:app",
                 "--host", "127.0.0.1", "--port", str(PORT)],
                cwd=str(src_dir)
            )
            log(f"源码模式启动 (PID: {proc.pid})")
        
        # 等待服务就绪
        log("等待服务启动...")
        for i in range(30):
            time.sleep(1)
            if check_port(PORT):
                log(f"服务已就绪 (等待 {i+1} 秒)")
                break
            # 显示进度
            print(f"\r  等待中... {i+1}/30 秒", end="", flush=True)
        else:
            log("错误：服务启动超时")
            input("\n按回车键退出...")
            return
        
        print()  # 换行
        
        # 打开浏览器
        log(f"打开浏览器: {URL}")
        webbrowser.open(URL)
        
        log("=" * 50)
        log("太玄智译已启动！")
        log("=" * 50)
        log(f"访问地址: {URL}")
        log(f"API 文档: {URL}/docs")
        log("")
        log("提示：关闭此窗口将停止服务")
        log("")
        
        # 保持运行
        input("按回车键停止服务并退出...")
        
        # 停止服务
        log("停止服务...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log("服务已停止")
        
    except Exception as e:
        log(f"错误: {e}")
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()
