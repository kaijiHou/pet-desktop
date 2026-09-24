param(
    [int]$WaitSeconds = 5
)

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7+ is required. Run scripts/verify_release.ps1 with pwsh."
}

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$releaseTools = Join-Path $PSScriptRoot "release_artifacts.py"
$zipPath = Join-Path $projectRoot "release\DesktopPet-windows-x64.zip"
$manifestPath = Join-Path $projectRoot "release\manifest.json"
$testRoot = Join-Path $projectRoot ".tmp\tests"
$extractDir = Join-Path $testRoot ("v53-extracted-" + [guid]::NewGuid().ToString("N"))

if (-not (Test-Path -LiteralPath $zipPath)) {
    throw "Release ZIP not found: $zipPath"
}

$null = New-Item -ItemType Directory -Path $extractDir -Force
$extractNote = Join-Path $extractDir "目录说明.md"
[System.IO.File]::WriteAllText($extractNote,
    "# Release 验证临时目录`r`n`r`n此目录由 scripts/verify_release.ps1 从 release ZIP 解压生成，仅用于新包黑盒启动检查；可重建，不放用户文件。`r`n",
    [System.Text.UTF8Encoding]::new($false))
& $python -B $releaseTools extract --zip-path $zipPath --destination $extractDir
if ($LASTEXITCODE -ne 0) { throw "Could not extract release ZIP safely." }
& $python -B $releaseTools verify --manifest $manifestPath --zip-path $zipPath --version "V5.3"
if ($LASTEXITCODE -ne 0) { throw "Release manifest or ZIP SHA256 verification failed." }

$packageDir = Join-Path $extractDir "DesktopPet"
$exePath = Join-Path $packageDir "DesktopPet.exe"
$process = Start-Process -FilePath $exePath -WorkingDirectory $packageDir -PassThru -WindowStyle Hidden

try {
    [Threading.Thread]::Sleep([TimeSpan]::FromSeconds($WaitSeconds))
    $process.Refresh()
    $running = -not $process.HasExited
    $responding = $running -and $process.Responding
    $webEngineCount = 0
    foreach ($file in [IO.Directory]::EnumerateFiles($packageDir, "*", [IO.SearchOption]::AllDirectories)) {
        if ([IO.Path]::GetFileName($file) -match "WebEngine|QtWebEngine|Chromium") { $webEngineCount++ }
    }
    $logPath = Join-Path $packageDir "logs\app.log"
    $logCreated = [IO.File]::Exists($logPath)
    $identityLogged = $false
    if ($logCreated) {
        & $python -B $releaseTools verify-log --manifest $manifestPath --log $logPath
        $identityLogged = $LASTEXITCODE -eq 0
    }
    $result = [ordered]@{
        extract_dir = $extractDir
        running = [bool]$running
        responding = [bool]$responding
        animation_catalog = Test-Path -LiteralPath (Join-Path $packageDir "_internal\assets\animations.json")
        user_assets_dir = Test-Path -LiteralPath (Join-Path $packageDir "assets")
        log_created = $logCreated
        build_identity_logged = $identityLogged
        webengine_files = $webEngineCount
    }
    foreach ($key in $result.Keys) { [Console]::WriteLine("{0}={1}", $key, $result[$key]) }
    if (-not $result.running -or -not $result.responding -or
        -not $result.animation_catalog -or -not $result.user_assets_dir -or
        -not $result.log_created -or -not $result.build_identity_logged -or $result.webengine_files -ne 0) {
        throw "Release verification failed."
    }
}
finally {
    $process.Refresh()
    if (-not $process.HasExited) {
        $process.Kill()
        $null = $process.WaitForExit(5000)
    }
}
