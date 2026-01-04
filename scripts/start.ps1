# PDF Mind Map Generator - Start Services
# This script starts all Docker services

Write-Host "Starting PDF Mind Map Generator services..." -ForegroundColor Cyan

# Check if Docker is running
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Navigate to project root (parent of scripts directory)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Start services
Write-Host "Starting Docker Compose services..." -ForegroundColor Yellow
docker compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Access the application at:" -ForegroundColor Cyan
    Write-Host "  Frontend:    http://localhost:3001"
    Write-Host "  Backend API: http://localhost:8000"
    Write-Host "  API Docs:    http://localhost:8000/docs"
    Write-Host "  Grafana:     http://localhost:3000 (admin/admin)"
    Write-Host "  Prometheus:  http://localhost:9090"
    Write-Host ""
    Write-Host "If this is your first time, run: .\scripts\pull-model.ps1" -ForegroundColor Yellow
} else {
    Write-Host "Error starting services. Check Docker logs for details." -ForegroundColor Red
    exit 1
}
