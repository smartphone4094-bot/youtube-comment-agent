# Builds the portable program: dist\MarketingAI\MarketingAI.exe and dist\MarketingAI.zip.
# Uses a clean venv (.venv-build) so only the app's own packages end up in the bundle.
# Usage: powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = if ($env:BUILD_PYTHON) { $env:BUILD_PYTHON } else { "python" }
$venv = Join-Path $PSScriptRoot ".venv-build"
$venvPython = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    & $python -m venv $venv
    if ($LASTEXITCODE) { throw "venv creation failed" }
}
& $venvPython -m pip install --disable-pip-version-check -q -r requirements-build.txt
if ($LASTEXITCODE) { throw "pip install failed" }

# PyInstaller wipes dist\MarketingAI, which may hold a running copy's keys and logged-in profiles.
# Park them outside, build and zip without them, then put them back.
$app = Join-Path $PSScriptRoot "dist\MarketingAI"
$keep = Join-Path $PSScriptRoot "build\user-files"
if (Test-Path $keep) { throw "$keep exists from an interrupted build; move its files back into $app first" }
$userFiles = @("settings.yaml", "data") | Where-Object { Test-Path (Join-Path $app $_) }
if ($userFiles) {
    New-Item -ItemType Directory -Force $keep | Out-Null
    foreach ($f in $userFiles) { Move-Item (Join-Path $app $f) $keep }
}
try {
    & $venvPython -m PyInstaller --noconfirm --clean MarketingAI.spec
    if ($LASTEXITCODE) { throw "PyInstaller failed" }

    $zip = Join-Path $PSScriptRoot "dist\MarketingAI.zip"
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path $app -DestinationPath $zip
    Write-Host "Built: dist\MarketingAI\MarketingAI.exe and $zip"
} finally {
    if ($userFiles) {
        New-Item -ItemType Directory -Force $app | Out-Null
        foreach ($f in $userFiles) { Move-Item (Join-Path $keep $f) $app }
        Remove-Item $keep
    }
}
