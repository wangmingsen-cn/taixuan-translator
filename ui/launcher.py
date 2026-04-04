# -*- coding: utf-8 -*-
"""
太玄智译 - 一键启动器
功能：双击 EXE → 弹出窗口 → 自动启动服务 → 进入界面
"""

import sys
import os
import subprocess
import time
import socket
import webbrowser
import threading
from pathlib import Path

# tkinter 是 Python 内置库，无需安装
import tkinter as tk
from tkinter import ttk

# ─── 路径配置 ────────────────────────────────────────────────
def get_base_dir():
    """获取基础目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

BASE_DIR = get_base_dir()
PORT = 8000
URL = f"http://127.0.0.1:{PORT}"

# ─── 日志 ────────────────────────────────────────────────────
LOG_DIR = Path.home() / ".taixuan_translator" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "launcher.log"

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def check_port(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_api_exe():
    """查找 API 服务 EXE"""
    candidates = [
        BASE_DIR / "app" / "taixuan-translator-api.exe",
        BASE_DIR / "taixuan-translator-api.exe",
        BASE_DIR / "_internal" / "taixuan-translator-api.exe",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None

# ─── 主窗口 ───────────────────────────────────────────────────
class LauncherWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("太玄智译 v1.0")
        self.root.geometry("520x320")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        
        # 居中
        self.center_window()
        
        # 服务进程
        self.process = None
        self.running = False
        
        # 创建 UI
        self.create_ui()
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 自动检查端口
        self.root.after(500, self.check_existing)
    
    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
    
    def create_ui(self):
        """创建 UI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 主框架
        main_frame = tk.Frame(self.root, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # 标题
        title = tk.Label(
            main_frame,
            text="太玄智译",
            font=("Microsoft YaHei UI", 28, "bold"),
            fg="#e94560",
            bg="#1a1a2e"
        )
        title.pack(pady=(10, 5))
        
        # 副标题
        subtitle = tk.Label(
            main_frame,
            text="PDF 精准翻译解决方案",
            font=("Microsoft YaHei UI", 11),
            fg="#a0a0a0",
            bg="#1a1a2e"
        )
        subtitle.pack(pady=(0, 20))
        
        # 状态标签
        self.status_var = tk.StringVar(value="等待启动...")
        self.status_label = tk.Label(
            main_frame,
            textvariable=self.status_var,
            font=("Microsoft YaHei UI", 10),
            fg="#4a9eff",
            bg="#1a1a2e"
        )
        self.status_label.pack(pady=5)
        
        # 进度条
        self.progress = ttk.Progressbar(
            main_frame,
            mode="indeterminate",
            length=300,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=10)
        style.configure("Custom.Horizontal.TProgressbar", 
                       thickness=4, 
                       background="#e94560")
        
        # 启动按钮
        self.btn_frame = tk.Frame(main_frame, bg="#1a1a2e")
        self.btn_frame.pack(pady=15)
        
        self.start_btn = tk.Button(
            self.btn_frame,
            text="▶ 启动太玄智译",
            font=("Microsoft YaHei UI", 12, "bold"),
            fg="white",
            bg="#e94560",
            activebackground="#d63050",
            activeforeground="white",
            relief=tk.FLAT,
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.start_service
        )
        self.start_btn.pack()
        
        # 提示
        tip = tk.Label(
            main_frame,
            text="启动后将自动打开浏览器访问 http://127.0.0.1:8000",
            font=("Microsoft YaHei UI", 8),
            fg="#606060",
            bg="#1a1a2e"
        )
        tip.pack(pady=(5, 0))
        
        # 版本信息
        version = tk.Label(
            main_frame,
            text="v1.0.0 | 太玄计算机软件开发工作室",
            font=("Microsoft YaHei UI", 8),
            fg="#404040",
            bg="#1a1a2e"
        )
        version.pack(side=tk.BOTTOM, pady=5)
    
    def check_existing(self):
        """检查是否已有服务运行"""
        if check_port(PORT):
            self.status_var.set("检测到服务已在运行")
            self.start_btn.config(text="🌐 打开界面", command=self.open_browser)
            self.progress.stop()
        else:
            self.status_var.set("就绪，点击启动")
    
    def start_service(self):
        """启动服务"""
        log("[Launcher] 开始启动服务...")
        
        self.start_btn.config(state=tk.DISABLED, text="启动中...")
        self.progress.start(10)
        self.status_var.set("正在启动 API 服务...")
        
        # 在后台线程启动服务
        thread = threading.Thread(target=self._start_service_thread, daemon=True)
        thread.start()
    
    def _start_service_thread(self):
        """后台线程：启动服务"""
        try:
            # 检查端口
            if check_port(PORT):
                self.root.after(0, self.on_service_ready)
                return
            
            # 查找 EXE
            api_exe = find_api_exe()
            
            if api_exe:
                log(f"[Launcher] 使用 EXE: {api_exe}")
                self.process = subprocess.Popen(
                    [str(api_exe), "--host", "127.0.0.1", "--port", str(PORT)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(api_exe.parent)
                )
            else:
                # 尝试从 Python 源码启动
                log("[Launcher] 未找到 EXE，从源码启动...")
                src_dir = Path(__file__).parent.parent.parent
                self.process = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn",
                     "taixuan_translator.api.main:app",
                     "--host", "127.0.0.1", "--port", str(PORT)],
                    cwd=str(src_dir)
                )
            
            # 等待服务就绪
            for i in range(30):
                time.sleep(1)
                if check_port(PORT):
                    log(f"[Launcher] 服务就绪 (等待 {i+1}s)")
                    self.root.after(0, self.on_service_ready)
                    return
            
            log("[Launcher] 服务启动超时")
            self.root.after(0, lambda: self.on_error("服务启动超时，请检查端口 8000 是否被占用"))
            
        except Exception as e:
            log(f"[Launcher] 错误: {e}")
            self.root.after(0, lambda: self.on_error(str(e)))
    
    def on_service_ready(self):
        """服务就绪"""
        self.progress.stop()
        self.status_var.set("✅ 服务已就绪，正在打开浏览器...")
        log("[Launcher] 服务就绪，打开浏览器")
        
        # 打开浏览器
        webbrowser.open(URL)
        
        # 更新按钮
        self.start_btn.config(
            state=tk.NORMAL,
            text="🌐 已启动，点击重新打开",
            command=self.open_browser
        )
        self.running = True
    
    def open_browser(self):
        """打开浏览器"""
        webbrowser.open(URL)
    
    def on_error(self, msg):
        """启动失败"""
        self.progress.stop()
        self.start_btn.config(state=tk.NORMAL, text="▶ 重试")
        self.status_var.set(f"❌ {msg}")
        log(f"[Launcher] 错误: {msg}")
    
    def on_close(self):
        """关闭窗口"""
        log("[Launcher] 关闭启动器窗口（服务保持运行）")
        self.root.destroy()

# ─── 入口 ────────────────────────────────────────────────────
if __name__ == "__main__":
    log("[Launcher] 启动器开始运行")
    window = LauncherWindow()
    window.root.mainloop()
