param(
    [switch]$SkipTests,
    [switch]$SkipDocAudit
)

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7+ is required. Run scripts/build_release.ps1 with pwsh."
}

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$releaseTools = Join-Path $PSScriptRoot "release_artifacts.py"
$pyinstaller = Join-Path $projectRoot ".venv\Scripts\pyinstaller.exe"
$buildDir = Join-Path $projectRoot "build"
$distDir = Join-Path $projectRoot "dist"
$tempRoot = Join-Path $projectRoot ".tmp"
$tempDir = Join-Path $projectRoot ".tmp\pyinstaller"
$cacheDir = $tempDir
$testTempDir = Join-Path $projectRoot ".tmp\tests"
$releaseVersion = "V5.3"
if ($SkipDocAudit) {
    $releaseDir = Join-Path $tempRoot ("v53-dev-release-" + [guid]::NewGuid().ToString("N"))
} else {
    $releaseDir = Join-Path $projectRoot "release"
}

$env:PYINSTALLER_CONFIG_DIR = $cacheDir
$null = New-Item -ItemType Directory -Path $tempRoot -Force
$tempRootNote = Join-Path $tempRoot "目录说明.md"
if (-not (Test-Path -LiteralPath $tempRootNote)) {
    [System.IO.File]::WriteAllText($tempRootNote,
        "# 临时工作区说明`r`n`r`n仅存放可重建的测试、构建和诊断临时输出；不放用户真实文件或正式交付物。`r`n",
        ([System.Text.UTF8Encoding]::new($false)))
}
$null = New-Item -ItemType Directory -Path $cacheDir -Force
$null = New-Item -ItemType Directory -Path $tempDir -Force
$tempNote = Join-Path $tempDir "目录说明.md"
if (-not (Test-Path -LiteralPath $tempNote)) {
    [System.IO.File]::WriteAllText($tempNote,
        "# PyInstaller 临时区`r`n`r`n仅存放本地构建缓存和临时数据；不放用户文件或正式交付物。`r`n",
        ([System.Text.UTF8Encoding]::new($false)))
}
$testTempNote = Join-Path $testTempDir "目录说明.md"
if (-not (Test-Path -LiteralPath $testTempNote)) {
    $null = New-Item -ItemType Directory -Path $testTempDir -Force
    [System.IO.File]::WriteAllText($testTempNote,
        "# 自动化测试临时数据`r`n`r`n仅存放 pytest 隔离文件与目录；测试结束后由 fixture 清理，不放用户文件。`r`n",
        ([System.Text.UTF8Encoding]::new($false)))
}

if (-not (Test-Path -LiteralPath $pyinstaller)) {
    throw "PyInstaller is missing. Install requirements-dev.txt first."
}

if (-not $SkipDocAudit) {
    $auditArgs = @(
        "--version", $releaseVersion,
        "--baseline", "6f62ca5af962f7485147cb6543e73072a4866471",
        "--summary", "docs/V53_CHANGE_SUMMARY.md",
        "--acceptance", "docs/V53_REAL_ACCEPTANCE.md",
        "--ui-review", "docs/V53_UI_REVIEW.md",
        "--extra-required", "docs/screenshots/v53/目录说明.md",
        "--extra-required", "docs/screenshots/v53/quick-panel-favorites.png",
        "--extra-required", "docs/screenshots/v53/favorite-folders.png",
        "--extra-required", "docs/screenshots/v53/favorite-folders-missing.png",
        "--extra-required", "docs/screenshots/v53/pocket-favorite-targets.png"
    )
    & $python -B (Join-Path $PSScriptRoot "audit_release_docs.py") @auditArgs --prebuild
    if ($LASTEXITCODE -ne 0) { throw "Pre-build release documentation audit failed; build aborted." }
}

foreach ($path in @($buildDir, $distDir, $releaseDir)) {
    $resolvedParent = [System.IO.Path]::GetFullPath((Split-Path -Parent $path))
    $resolvedTarget = [System.IO.Path]::GetFullPath($path)
    if ($resolvedParent -ne [System.IO.Path]::GetFullPath($projectRoot)) {
        if (-not ($SkipDocAudit -and $resolvedTarget.StartsWith([System.IO.Path]::GetFullPath($tempRoot), [StringComparison]::OrdinalIgnoreCase))) {
            throw "Refusing to clean path outside project root or temporary build root: $resolvedTarget"
        }
    }
    if (Test-Path -LiteralPath $resolvedTarget) {
        if ($resolvedTarget -eq [System.IO.Path]::GetFullPath($releaseDir) -and -not $SkipDocAudit) {
            $stamp = [DateTimeOffset]::Now.ToString("yyyyMMdd-HHmmss-fff")
            $backupDir = Join-Path $tempRoot ("v53-previous-release-" + $stamp)
            $null = New-Item -ItemType Directory -Path $backupDir
            $backupReleaseDir = Join-Path $backupDir "release"
            $null = New-Item -ItemType Directory -Path $backupReleaseDir
            Copy-Item -Path (Join-Path $resolvedTarget "*") -Destination $backupReleaseDir -Recurse -Force
            $backupNote = "# Previous release archive`r`n`r`nSource: $resolvedTarget`r`nCopy: $resolvedTarget/* -> $backupReleaseDir/`r`nThis recoverable copy is preserved before the V5.3 clean build. It contains only the previous generated release output.`r`n"
            [System.IO.File]::WriteAllText((Join-Path $backupDir "目录说明.md"), $backupNote, [System.Text.UTF8Encoding]::new($false))
            $oldZip = Join-Path $resolvedTarget "DesktopPet-windows-x64.zip"
            $savedZip = Join-Path $backupReleaseDir "DesktopPet-windows-x64.zip"
            if ((Test-Path -LiteralPath $oldZip) -and (Test-Path -LiteralPath $savedZip)) {
                $oldHash = (& $python -B $releaseTools sha256 $oldZip).Trim()
                $savedHash = (& $python -B $releaseTools sha256 $savedZip).Trim()
                if ($oldHash -ne $savedHash) { throw "Previous release backup verification failed; original release preserved." }
            }
        }
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
}

if (-not $SkipTests) {
    $env:TEMP = $testTempDir
    $env:TMP = $testTempDir
    & $python -B -m pytest (Join-Path $projectRoot "tests") -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; release build aborted." }
}

# Build identity (V5.3): write build_info.json BEFORE PyInstaller so the
# spec packs it; app_version.py reads it at runtime, never invoking git.
$gitSha = (& git rev-parse HEAD).Trim()
$buildTime = [DateTimeOffset]::Now.ToString("o")
& $python -B $releaseTools write-build-info (Join-Path $projectRoot "build_info.json") `
    --version $releaseVersion --git-sha $gitSha --build-time $buildTime
if ($LASTEXITCODE -ne 0) { throw "Could not write build identity." }

$env:TEMP = $tempDir
$env:TMP = $tempDir
& $pyinstaller --noconfirm --clean `
    --workpath $buildDir `
    --distpath $distDir `
    (Join-Path $projectRoot "pet-desktop.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

foreach ($outputDir in @($buildDir, $distDir)) {
    $note = Join-Path $outputDir "目录说明.md"
    if (-not (Test-Path -LiteralPath $note)) {
        [System.IO.File]::WriteAllText($note,
            "# 构建输出说明`r`n`r`n此目录由 scripts/build_release.ps1 生成，仅含可重建的构建产物；不放用户文件。`r`n",
            ([System.Text.UTF8Encoding]::new($false)))
    }
}

$packageDir = Join-Path $releaseDir "DesktopPet"
$null = New-Item -ItemType Directory -Path $packageDir -Force
Copy-Item -Path (Join-Path $distDir "DesktopPet\*") -Destination $packageDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $packageDir
$null = New-Item -ItemType Directory -Path (Join-Path $packageDir "assets") -Force
$assetReadme = Join-Path $packageDir "assets\README.md"
if (-not (Test-Path -LiteralPath $assetReadme)) {
    [System.IO.File]::WriteAllText($assetReadme,
        "# Optional custom character assets`r`n`r`nPlace only character images or sprite sheets you have rights to use here. The application includes its own neutral fallback. See the packaged CUSTOM_CHARACTER.txt for details.`r`n",
        ([System.Text.UTF8Encoding]::new($false)))
}
$releaseNote = Join-Path $releaseDir "目录说明.md"
if (-not (Test-Path -LiteralPath $releaseNote)) {
    [System.IO.File]::WriteAllText($releaseNote,
        "# 发布输出说明`r`n`r`nDesktopPet-windows-x64.zip 是交付包，manifest.json 记录版本、Git SHA 与 ZIP SHA256。DesktopPet/ 为解压前的打包目录。此目录由构建脚本重建。`r`n",
        ([System.Text.UTF8Encoding]::new($false)))
}

$assetNote = @"
Custom character (optional)
===========================

Put your own 124x93-frame sprite sheet here:
  assets\clippy_sheet.png

Without it, DesktopPet displays the built-in neutral paperclip placeholder.
The repository does not redistribute Microsoft Clippy artwork.
"@
[System.IO.File]::WriteAllText((Join-Path $packageDir "CUSTOM_CHARACTER.txt"), $assetNote,
    [System.Text.UTF8Encoding]::new($false))

$zipPath = Join-Path $releaseDir "DesktopPet-windows-x64.zip"
& $python -B $releaseTools package --package-dir $packageDir --release-dir $releaseDir `
    --zip-path $zipPath --version $releaseVersion --git-sha $gitSha --build-time $buildTime
if ($LASTEXITCODE -ne 0) { throw "Could not package release artifacts." }

if (-not $SkipDocAudit) {
    $summaryPath = Join-Path $projectRoot "docs\V53_CHANGE_SUMMARY.md"
    $summaryText = [System.IO.File]::ReadAllText($summaryPath)
    $pendingPattern = '(?m)^Artifact ZIP SHA256: pending\s*$'
    $releaseHeadPattern = '(?m)^Release built from Git HEAD: pending\s*$'
    if ([regex]::Matches($summaryText, $pendingPattern).Count -ne 1 -or
        [regex]::Matches($summaryText, $releaseHeadPattern).Count -ne 1) {
        throw "Expected one generated release HEAD and ZIP hash field in $summaryPath."
    }
    $zipSha = (& $python -B $releaseTools sha256 $zipPath).Trim()
    $summaryText = [regex]::Replace($summaryText, $pendingPattern, "Artifact ZIP SHA256: $zipSha")
    $summaryText = [regex]::Replace($summaryText, $releaseHeadPattern, "Release built from Git HEAD: $gitSha")
    [System.IO.File]::WriteAllText($summaryPath, $summaryText, [System.Text.UTF8Encoding]::new($false))
    & $python -B (Join-Path $PSScriptRoot "audit_release_docs.py") @auditArgs
    if ($LASTEXITCODE -ne 0) { throw "Final release documentation audit failed; release is not accepted." }
}
[Console]::WriteLine("Release: $releaseDir")
