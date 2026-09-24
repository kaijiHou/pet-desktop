"""Audit version documents against committed Git changes and required files."""

import argparse
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


SUMMARY_SECTIONS = (
    "Baseline", "本轮目标", "修改前问题", "本轮实际修改", "文件级变化",
    "新增功能", "修复 Bug", "删除/弃用", "测试", "真实验收", "Release",
    "Remaining Known Issues", "本轮未完成项", "Commit 列表", "最终状态",
)
BASE_REQUIRED = (
    "docs/DEVELOPMENT_LOG.md", "docs/TEST_REPORT.md", "docs/KNOWN_ISSUES.md",
    "docs/ARCHITECTURE.md",
)
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD|PLACEHOLDER)\b|（回填）|\(回填\)", re.IGNORECASE)
CHANGE_LINE_RE = re.compile(r"^\s*([AMDR])\s+(.+?)\s*$")


def _run_git(root, *args):
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def parse_name_status_z(output):
    """Parse `git diff --name-status -z`, preserving rename pairs as one key."""
    fields = output.split("\0")
    changes = {}
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        index += 1
        kind = status[0]
        if kind == "R":
            if index + 1 >= len(fields):
                raise ValueError("truncated rename record in git name-status output")
            old, new = fields[index:index + 2]
            index += 2
            changes[f"{old} -> {new}"] = "R"
        elif kind in {"A", "M", "D"}:
            if index >= len(fields):
                raise ValueError("truncated path in git name-status output")
            changes[fields[index]] = kind
            index += 1
        else:
            raise ValueError(f"unsupported Git change status: {status}")
    return changes


def committed_changes(root, baseline, head="HEAD"):
    output = _run_git(root, "diff", "--name-status", "-z", "-M", f"{baseline}..{head}")
    return parse_name_status_z(output)


def summary_changes(summary_text):
    """Read status/path rows from the first fenced block below section 5."""
    heading = re.search(r"^## 5\. 文件级变化\s*$", summary_text, re.MULTILINE)
    if not heading:
        raise ValueError("summary is missing section 5 文件级变化")
    fence_start = summary_text.find("```", heading.end())
    fence_end = summary_text.find("```", fence_start + 3) if fence_start >= 0 else -1
    if fence_start < 0 or fence_end < 0:
        raise ValueError("section 5 must contain a fenced Git name-status list")
    block = summary_text[fence_start + 3:fence_end]
    if "\n" in block and block.split("\n", 1)[0].strip().lower() in {"text", "diff", ""}:
        block = block.split("\n", 1)[1]
    changes = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        match = CHANGE_LINE_RE.match(line)
        if not match:
            raise ValueError(f"invalid name-status row in summary: {line}")
        status, path = match.groups()
        changes[path] = status
    return changes


def compare_changes(actual, documented, summary_path):
    self_path = PurePosixPath(summary_path).as_posix()
    actual = {path: status for path, status in actual.items() if path != self_path}
    documented = {path: status for path, status in documented.items() if path != self_path}
    missing = sorted(actual.keys() - documented.keys())
    extra = sorted(documented.keys() - actual.keys())
    mismatches = sorted(
        (path, actual[path], documented[path])
        for path in actual.keys() & documented.keys()
        if actual[path] != documented[path]
    )
    return actual, documented, missing, extra, mismatches


def artifact_hash_is_valid(summary_text, allow_pending=False):
    if re.search(r"Artifact ZIP SHA256:\s*`?[0-9a-f]{64}`?", summary_text, re.IGNORECASE):
        return True
    return bool(allow_pending and re.search(
        r"Artifact ZIP SHA256:\s*pending\s*$", summary_text, re.IGNORECASE | re.MULTILINE,
    ))


def _relative(path, root):
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = root / resolved
    return resolved


def audit(args):
    root = Path(args.root).resolve()
    summary_path = _relative(args.summary, root)
    acceptance_path = _relative(args.acceptance, root)
    summary_rel = summary_path.relative_to(root).as_posix()
    acceptance_rel = acceptance_path.relative_to(root).as_posix()
    required = list(BASE_REQUIRED) + [summary_rel, acceptance_rel] + args.extra_required
    errors = []

    for relative in required:
        target = root / relative
        if not target.is_file() or not target.read_text(encoding="utf-8").strip():
            errors.append(f"required file missing or empty: {relative}")

    summary = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
    acceptance = acceptance_path.read_text(encoding="utf-8") if acceptance_path.is_file() else ""
    for number, title in enumerate(SUMMARY_SECTIONS, 1):
        if f"## {number}. {title}" not in summary:
            errors.append(f"summary section missing: ## {number}. {title}")
    if not re.search(rf"^# {re.escape(args.version)} Change Summary\s*$", summary, re.MULTILINE):
        errors.append(f"summary title must be '# {args.version} Change Summary'")
    if not re.search(rf"^# {re.escape(args.version)} Real Acceptance\s*$", acceptance, re.MULTILINE):
        errors.append(f"acceptance title must be '# {args.version} Real Acceptance'")

    for label, pattern in (
        ("baseline SHA", rf"Baseline HEAD:\s*`?[0-9a-f]{{40}}`?"),
        ("implementation scope SHA", r"Summary scope implementation HEAD:\s*`?[0-9a-f]{40}`?"),
        ("release Git SHA", r"Release built from Git HEAD:\s*`?[0-9a-f]{40}`?"),
    ):
        if not re.search(pattern, summary, re.IGNORECASE):
            errors.append(f"summary field missing or malformed: {label}")
    if not artifact_hash_is_valid(summary, allow_pending=args.prebuild):
        errors.append("summary field missing or malformed: artifact ZIP SHA256")

    formal_docs = (summary, acceptance, (root / args.ui_review).read_text(encoding="utf-8")
                   if args.ui_review and (root / args.ui_review).is_file() else "")
    placeholders = sorted({match.group(0) for content in formal_docs
                           for match in PLACEHOLDER_RE.finditer(content)})
    if placeholders:
        errors.append("formal documentation contains placeholders: " + ", ".join(placeholders))

    try:
        actual = committed_changes(root, args.baseline, args.head)
        documented = summary_changes(summary)
        actual, documented, missing, extra, mismatches = compare_changes(
            actual, documented, summary_rel,
        )
    except (RuntimeError, ValueError) as exc:
        errors.append(f"Git/status audit failed: {exc}")
        actual, documented, missing, extra, mismatches = {}, {}, [], [], []

    print(f"Changed files: {len(actual)}")
    print(f"Documented files: {len(documented)}")
    print(f"Missing: {len(missing)}")
    for path in missing:
        print(f"  MISSING {actual[path]} {path}")
    print(f"Extra: {len(extra)}")
    for path in extra:
        print(f"  EXTRA {documented[path]} {path}")
    print(f"Status mismatches: {len(mismatches)}")
    for path, real, recorded in mismatches:
        print(f"  STATUS {path}: Git={real}, Summary={recorded}")
    print(f"Missing={len(missing)} Extra={len(extra)} Status mismatches={len(mismatches)} Placeholder={len(placeholders)}")

    if missing or extra or mismatches or errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"{args.version} release documentation audit: PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="release label, e.g. V5.3")
    parser.add_argument("--baseline", required=True, help="full Git baseline commit")
    parser.add_argument("--summary", required=True, help="Change Summary path relative to project root")
    parser.add_argument("--acceptance", required=True, help="Real Acceptance path relative to project root")
    parser.add_argument("--ui-review", default="", help="optional UI review Markdown path")
    parser.add_argument("--prebuild", action="store_true",
                        help="allow the exact pending artifact hash marker; build scripts must run a full audit afterward")
    parser.add_argument("--extra-required", action="append", default=[],
                        help="additional required path; can be passed more than once")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]),
                        help=argparse.SUPPRESS)
    parser.add_argument("--head", default="HEAD", help=argparse.SUPPRESS)
    return audit(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
