#!/usr/bin/env pwsh
# Launcher script for demo controller - handles venv automatically

$venvPython = ".\.venv\Scripts\python.exe"

if (-Not (Test-Path $venvPython)) {
    Write-Host "Error: Virtual environment not found at .venv" -ForegroundColor Red
    Write-Host "Run from the splitflap directory!" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "Starting Splitflap Demo Controller..." -ForegroundColor Green
Write-Host ""

& $venvPython demo_controller.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Demo controller exited with error" -ForegroundColor Red
    pause
}
