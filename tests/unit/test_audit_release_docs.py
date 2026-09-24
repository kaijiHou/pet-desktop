"""Contracts for reusable release-document Git status auditing."""

import pytest

from scripts.audit_release_docs import (
    artifact_hash_is_valid, compare_changes, parse_name_status_z, summary_changes,
)


@pytest.mark.unit
def test_name_status_parser_handles_add_modify_delete_and_rename():
    parsed = parse_name_status_z(
        "M\0docs/changed.md\0A\0docs/added.md\0D\0docs/removed.md\0"
        "R100\0docs/old name.md\0docs/new name.md\0"
    )
    assert parsed == {
        "docs/changed.md": "M",
        "docs/added.md": "A",
        "docs/removed.md": "D",
        "docs/old name.md -> docs/new name.md": "R",
    }


@pytest.mark.unit
def test_summary_status_mismatch_is_not_hidden():
    text = """## 5. 文件级变化

```text
M docs/ARCHITECTURE.md
A docs/new.md
```
"""
    documented = summary_changes(text)
    _, _, missing, extra, mismatches = compare_changes(
        {"docs/ARCHITECTURE.md": "M", "docs/new.md": "M"}, documented, "docs/V53_CHANGE_SUMMARY.md",
    )
    assert missing == [] and extra == []
    assert mismatches == [("docs/new.md", "M", "A")]


@pytest.mark.unit
def test_pending_artifact_hash_is_prebuild_only():
    pending = "Artifact ZIP SHA256: pending\n"
    actual = "Artifact ZIP SHA256: " + "a" * 64
    assert artifact_hash_is_valid(pending, allow_pending=True)
    assert not artifact_hash_is_valid(pending)
    assert artifact_hash_is_valid(actual)
