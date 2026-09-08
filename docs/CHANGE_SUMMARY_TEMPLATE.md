# CHANGE_SUMMARY_TEMPLATE

> 从 V5.0 起的永久项目规范：每个大版本（V51、V52、V60…）必须复制本模板为
> `docs/Vxx_CHANGE_SUMMARY.md`，随开发实时更新，与代码同一轮 commit/push。
> 没有这份文件，该版本视为交付不完整，不允许写 DONE。
> 复制后不要改动章节结构；没有内容的章节明确写"无"。

```markdown
# Vxx Change Summary

## 1. Baseline

Baseline HEAD: <git sha>
Branch: master
Date: <YYYY-MM-DD>
Environment: Windows 10.0.19045 x64 / Python 3.11.15 / PyQt5 5.15.11
GUI automation availability: available / unavailable（如实记录；禁止虚构"用户禁止"）

## 2. 本轮目标

<为什么做这个版本，2~5 行>

## 3. 修改前问题

逐项：编号 / 用户表现 / 代码根因 / 证据。例如：

- VXX-01：<表现>；根因 <…>；证据 <文件:行 / 测试 / 日志>

## 4. 本轮实际修改

逐项写（不允许只写"优化UI"/"修复bug"）：

### VXX-01
- 修改内容：
- 修改文件：
- 修改前：
- 修改后：
- 根因：
- 实现：

## 5. 文件级变化

`git diff --name-status <BASELINE>..HEAD` 的真实输出 + 每个重要文件为什么改。
必须包含本轮新增的文档自身。

## 6. 新增功能

无 / 列表。

## 7. 修复 Bug

真实 Bug 列表（带证据）。

## 8. 删除/弃用

无 / 列表（含保持 disabled 的模块说明）。

## 9. 测试

每条：命令 / 结果 / 耗时 / PASS|FAIL。

## 10. 真实验收

截图 / 鼠标 / DPI / Explorer / Fresh EXE。
状态只允许 PASS / FAIL / NOT TESTED / BLOCKED。
截图注明：rendered screenshot PASS ≠ human visual quality PASS。

## 11. Release

- Final repository HEAD: <docs 最终 commit>
- Release built from Git HEAD: <build 所用代码 commit>
- Artifact ZIP SHA256: <哈希>
- Build time: <时间>

规范：Git commit SHA 与 Artifact ZIP SHA256 必须明确分开标注，
禁止使用"candidate SHA"这类模糊叫法。

## 12. Remaining Known Issues

## 13. 本轮未完成项

## 14. Commit 列表

`git log --oneline <BASELINE>..HEAD` 真实输出。

## 15. 最终状态

DONE / PARTIAL（附一句理由）
```
