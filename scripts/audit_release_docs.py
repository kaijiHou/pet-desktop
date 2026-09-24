"""Check the required V5.2 release documents and summary fields."""

import argparse
from pathlib import Path
import re
import sys


SECTIONS = [
    "Baseline", "本轮目标", "修改前问题", "本轮实际修改", "文件级变化",
    "新增功能", "修复 Bug", "删除/弃用", "测试", "真实验收", "Release",
    "Remaining Known Issues", "本轮未完成项", "Commit 列表", "最终状态",
]
REQUIRED_FILES = [
    "docs/V52_CHANGE_SUMMARY.md",
    "docs/V52_REAL_ACCEPTANCE.md",
    "docs/FAVORITE_FOLDERS.md",
    "docs/DEVELOPMENT_LOG.md",
    "docs/TEST_REPORT.md",
    "docs/KNOWN_ISSUES.md",
    "docs/ARCHITECTURE.md",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", nargs="?", default="docs/V52_CHANGE_SUMMARY.md",
                        help="change-summary path relative to the project root")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    summary_path = Path(args.summary)
    if not summary_path.is_absolute():
        summary_path = root / summary_path

    missing = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            missing.append(f"required file: {relative}")

    if not summary_path.is_file():
        missing.append(f"summary file: {summary_path}")
        summary = ""
    else:
        summary = summary_path.read_text(encoding="utf-8")

    for number, title in enumerate(SECTIONS, start=1):
        heading = f"## {number}. {title}"
        if heading not in summary:
            missing.append(f"summary section: {heading}")

    for label, pattern in (
        ("Baseline HEAD", r"Baseline HEAD:\s*`?[0-9a-f]{40}`?"),
        ("release Git HEAD", r"Release built from Git HEAD:\s*\*\*[0-9a-f]{40}\*\*"),
        ("artifact ZIP SHA256", r"Artifact ZIP SHA256:\s*\*\*[0-9a-f]{64}\*\*"),
        ("final repository HEAD", r"Final repository HEAD:\s*(?:\*\*[0-9a-f]{40}\*\*|此 Change Summary 所在文档提交)"),
    ):
        if not re.search(pattern, summary, re.IGNORECASE):
            missing.append(f"summary field: {label}")

    for placeholder in ("<git sha>", "<YYYY-MM-DD>", "Vxx", "TODO", "TBD"):
        if placeholder.casefold() in summary.casefold():
            missing.append(f"unfilled placeholder: {placeholder}")

    for item in missing:
        print(f"MISSING: {item}")
    print(f"Missing={len(missing)}")
    if missing:
        return 1
    print("Release documentation audit: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
