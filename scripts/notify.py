"""
Hardening progress notifier.
Usage: python scripts/notify.py "STAGE N" "Short description"
"""

import sys
import os
import datetime
import platform

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "hardening_progress.log")


def beep() -> None:
    if platform.system() == "Windows":
        try:
            import winsound
            for _ in range(2):
                winsound.Beep(1000, 200)
            return
        except Exception:
            pass
    elif platform.system() == "Darwin":
        os.system("afplay /System/Library/Sounds/Glass.aiff 2>/dev/null")
        return
    # Fallback: terminal bell
    print("\a", end="", flush=True)


def banner(stage: str, message: str) -> str:
    title = f"  \u2705 {stage} COMPLETE \u2014 {message}  "
    width = max(len(title) + 2, 44)
    bar = "\u2550" * width
    return (
        f"\n\u2554{bar}\u2557\n"
        f"\u2551{title.center(width)}\u2551\n"
        f"\u255a{bar}\u255d\n"
    )


def log_entry(stage: str, message: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.abspath(LOG_FILE)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {stage} COMPLETE — {message}\n")


def notify(stage: str, message: str) -> None:
    beep()
    print(banner(stage, message))
    log_entry(stage, message)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/notify.py <STAGE> <MESSAGE>")
        sys.exit(1)
    notify(sys.argv[1], sys.argv[2])
