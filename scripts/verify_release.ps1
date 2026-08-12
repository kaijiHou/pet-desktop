param(
    [int]$WaitSeconds = 5
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$zipPath = Join-Path $projectRoot "release\DesktopPet-windows-x64.zip"
$testRoot = Join-Path $projectRoot ".tmp\tests"
$extractDir = Join-Path $testRoot ("phase18-extracted-" + [guid]::NewGuid().ToString("N"))

if (-not (Test-Path -LiteralPath $zipPath)) {
    throw "Release ZIP not found: $zipPath"
}

New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir

$packageDir = Join-Path $extractDir "DesktopPet"
$exePath = Join-Path $packageDir "DesktopPet.exe"
$process = Start-Process -FilePath $exePath -WorkingDirectory $packageDir -PassThru
Start-Sleep -Seconds $WaitSeconds

try {
    $live = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
    $webEngineFiles = @(
        Get-ChildItem -LiteralPath $packageDir -Recurse -Force |
            Where-Object { $_.Name -match "WebEngine|QtWebEngine|Chromium" }
    )
    $result = [ordered]@{
        extract_dir = $extractDir
        running = [bool]$live
        responding = [bool]($live -and $live.Responding)
        process_count = @(Get-Process DesktopPet -ErrorAction SilentlyContinue).Count
        animation_catalog = Test-Path -LiteralPath (Join-Path $packageDir "_internal\assets\animations.json")
        user_assets_dir = Test-Path -LiteralPath (Join-Path $packageDir "assets")
        log_created = Test-Path -LiteralPath (Join-Path $packageDir "logs\app.log")
        webengine_files = $webEngineFiles.Count
    }
    $result | ConvertTo-Json
    if (-not $result.running -or -not $result.responding -or
        -not $result.animation_catalog -or -not $result.user_assets_dir -or
        -not $result.log_created -or $result.webengine_files -ne 0) {
        throw "Release verification failed."
    }
}
finally {
    if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
        Stop-Process -Id $process.Id
    }
}
