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

& $venvPython -m PyInstaller --noconfirm --clean MarketingAI.spec
if ($LASTEXITCODE) { throw "PyInstaller failed" }

$zip = Join-Path $PSScriptRoot "dist\MarketingAI.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $PSScriptRoot "dist\MarketingAI") -DestinationPath $zip
Write-Host "Built: dist\MarketingAI\MarketingAI.exe and $zip"
