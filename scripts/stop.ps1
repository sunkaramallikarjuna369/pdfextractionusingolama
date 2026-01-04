# PDF Mind Map Generator - Stop Services
# This script stops all Docker services

Write-Host "Stopping PDF Mind Map Generator services..." -ForegroundColor Cyan

# Navigate to project root (parent of scripts directory)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Stop services
docker compose down

if ($LASTEXITCODE -eq 0) {
    Write-Host "Services stopped successfully!" -ForegroundColor Green
} else {
    Write-Host "Error stopping services." -ForegroundColor Red
    exit 1
}
