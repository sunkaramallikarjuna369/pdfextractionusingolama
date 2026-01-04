# PDF Mind Map Generator - Cleanup
# This script stops services and removes all volumes

Write-Host "WARNING: This will stop all services and remove all data!" -ForegroundColor Red
Write-Host ""

$confirmation = Read-Host "Are you sure you want to continue? (y/N)"
if ($confirmation -ne "y" -and $confirmation -ne "Y") {
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Cleaning up PDF Mind Map Generator..." -ForegroundColor Cyan

# Navigate to project root (parent of scripts directory)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Stop services and remove volumes
Write-Host "Stopping services and removing volumes..." -ForegroundColor Yellow
docker compose down -v

# Remove network if it exists
Write-Host "Removing network..." -ForegroundColor Yellow
docker network rm pdf-mindmap-network 2>$null

# Prune unused volumes
Write-Host "Pruning unused volumes..." -ForegroundColor Yellow
docker volume prune -f

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Cleanup completed successfully!" -ForegroundColor Green
    Write-Host "Run .\scripts\start.ps1 to start fresh." -ForegroundColor Cyan
} else {
    Write-Host "Cleanup completed with some warnings." -ForegroundColor Yellow
}
