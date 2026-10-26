"""程序入口。

用法：
    python run.py
"""
import io
import os
import sys

# Windows 控制台默认 GBK，中文输出会报错；统一转 UTF-8
if sys.stdout and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (ValueError, AttributeError):
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from akcalc.ui.app import main

if __name__ == "__main__":
    main()