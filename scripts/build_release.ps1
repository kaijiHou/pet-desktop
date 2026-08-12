param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pyinstaller = Join-Path $projectRoot ".venv\Scripts\pyinstaller.exe"
$buildDir = Join-Path $projectRoot "build"
$distDir = Join-Path $projectRoot "dist"
$releaseDir = Join-Path $projectRoot "release"
$cacheDir = Join-Path $projectRoot ".cache\pyinstaller"
$tempDir = Join-Path $projectRoot ".tmp\pyinstaller"

$env:PYINSTALLER_CONFIG_DIR = $cacheDir
$env:TEMP = $tempDir
$env:TMP = $tempDir
New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $pyinstaller)) {
    throw "PyInstaller is missing. Install requirements-dev.txt first."
}

foreach ($path in @($buildDir, $distDir, $releaseDir)) {
    $resolvedParent = [System.IO.Path]::GetFullPath((Split-Path -Parent $path))
    $resolvedTarget = [System.IO.Path]::GetFullPath($path)
    if ($resolvedParent -ne [System.IO.Path]::GetFullPath($projectRoot)) {
        throw "Refusing to clean path outside project root: $resolvedTarget"
    }
    if (Test-Path -LiteralPath $resolvedTarget) {
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
}

if (-not $SkipTests) {
    & $python -m pytest (Join-Path $projectRoot "tests") -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; release build aborted." }
}

& $pyinstaller --noconfirm --clean `
    --workpath $buildDir `
    --distpath $distDir `
    (Join-Path $projectRoot "pet-desktop.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$packageDir = Join-Path $releaseDir "DesktopPet"
New-Item -ItemType Directory -Path $packageDir -Force | Out-Null
Copy-Item -Path (Join-Path $distDir "DesktopPet\*") -Destination $packageDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $packageDir
New-Item -ItemType Directory -Path (Join-Path $packageDir "assets") -Force | Out-Null

$assetNote = @"
Custom character (optional)
===========================

Put your own 124x93-frame sprite sheet here:
  assets\clippy_sheet.png

Without it, DesktopPet displays the built-in neutral paperclip placeholder.
The repository does not redistribute Microsoft Clippy artwork.
"@
$assetNote | Set-Content -LiteralPath (Join-Path $packageDir "CUSTOM_CHARACTER.txt") -Encoding UTF8

$zipPath = Join-Path $releaseDir "DesktopPet-windows-x64.zip"
Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -CompressionLevel Optimal

$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest = [ordered]@{
    name = "DesktopPet"
    format = "windows-x64-one-folder"
    entrypoint = "DesktopPet\DesktopPet.exe"
    zip = "DesktopPet-windows-x64.zip"
    sha256 = $hash
    built_at = (Get-Date).ToString("o")
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $releaseDir "manifest.json") -Encoding UTF8

Write-Output "Release: $releaseDir"
Write-Output "SHA256: $hash"
