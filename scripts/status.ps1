# PDF Mind Map Generator - Service Status
# This script shows the status of all Docker services

Write-Host "PDF Mind Map Generator - Service Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to project root (parent of scripts directory)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Check Docker status
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is not running!" -ForegroundColor Red
    exit 1
}

Write-Host "Docker: Running" -ForegroundColor Green
Write-Host ""

# Show container status
Write-Host "Container Status:" -ForegroundColor Yellow
docker compose ps

Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Yellow
Write-Host "  Frontend:    http://localhost:3001"
Write-Host "  Backend API: http://localhost:8000"
Write-Host "  API Docs:    http://localhost:8000/docs"
Write-Host "  Grafana:     http://localhost:3000"
Write-Host "  Prometheus:  http://localhost:9090"
Write-Host "  Loki:        http://localhost:3100"
Write-Host "  Ollama:      http://localhost:11434"

Write-Host ""
Write-Host "Health Checks:" -ForegroundColor Yellow

# Check each service
$services = @(
    @{Name="Backend"; Port=8000; Path="/health"},
    @{Name="Frontend"; Port=3001; Path="/"},
    @{Name="Grafana"; Port=3000; Path="/api/health"},
    @{Name="Prometheus"; Port=9090; Path="/-/healthy"},
    @{Name="Loki"; Port=3100; Path="/ready"},
    @{Name="Ollama"; Port=11434; Path="/"}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)$($service.Path)" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  $($service.Name): OK" -ForegroundColor Green
        } else {
            Write-Host "  $($service.Name): Warning (Status: $($response.StatusCode))" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  $($service.Name): Not responding" -ForegroundColor Red
    }
}
