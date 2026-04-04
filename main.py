"""
太玄智译 - 主程序入口
"""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def main() -> None:
    """应用程序主入口"""
    # 初始化日志
    from taixuan_translator.core.utils import setup_logging
    setup_logging()

    # 初始化数据库
    from taixuan_translator.data.database import init_database
    init_database()

    logger.info("太玄智译 启动中...")

    # 启动 PyQt6 UI
    try:
        from PyQt6.QtWidgets import QApplication  # type: ignore[import]
        from taixuan_translator.ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("太玄智译")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("太玄计算机软件开发工作室")

        window = MainWindow()
        window.show()

        logger.info("太玄智译 UI 已启动")
        sys.exit(app.exec())

    except ImportError as e:
        logger.error(f"PyQt6 未安装，无法启动GUI: {e}")
        logger.info("请运行: pip install PyQt6")
        sys.exit(1)


if __name__ == "__main__":
    main()
