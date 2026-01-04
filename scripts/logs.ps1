# PDF Mind Map Generator - View Logs
# This script shows logs from Docker services

param(
    [string]$Service = "",
    [switch]$Follow = $false,
    [int]$Tail = 100
)

Write-Host "Viewing logs..." -ForegroundColor Cyan

# Navigate to project root (parent of scripts directory)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Build command
$cmd = "docker compose logs"

if ($Tail -gt 0) {
    $cmd += " --tail=$Tail"
}

if ($Follow) {
    $cmd += " -f"
}

if ($Service -ne "") {
    $cmd += " $Service"
}

Write-Host "Running: $cmd" -ForegroundColor Yellow
Write-Host ""

# Execute
Invoke-Expression $cmd
