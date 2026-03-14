"""Shared utilities for SWIFT (console output, logging)."""

from __future__ import annotations

import os
import time


class Console:
    """ANSI-styled console output with a global quiet toggle."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    ITALIC = "\033[3m"

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"

    is_quiet = False

    @staticmethod
    def section(title):
        if not Console.is_quiet:
            print(f"\n{Console.MAGENTA}{Console.BOLD}{title}{Console.RESET}")

    @staticmethod
    def warn(msg):
        if not Console.is_quiet:
            print(f"{Console.YELLOW}{Console.BOLD}{msg}{Console.RESET}")

    @staticmethod
    def info(msg):
        if not Console.is_quiet:
            print(f"{Console.CYAN}{msg}{Console.RESET}")

    @staticmethod
    def success(msg):
        if not Console.is_quiet:
            print(f"{Console.GREEN}{Console.BOLD}{msg}{Console.RESET}")


class Logger:
    """Append-only file logger for download sessions."""

    def __init__(self, output_dir: str):
        self.log_path = os.path.join(output_dir, "swift.log")

    def log(self, level: str, msg: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_path, "a") as f:
                f.write(f"[{timestamp}] [{level}] {msg}\n")
        except Exception:
            pass
