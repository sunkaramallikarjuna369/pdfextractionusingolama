# PDF Mind Map Generator - Pull Ollama Model
# This script pulls the required LLM model into Ollama

param(
    [string]$Model = "llama2"
)

Write-Host "Pulling Ollama model: $Model" -ForegroundColor Cyan

# Check if Ollama container is running
$ollamaRunning = docker ps --filter "name=pdf-mindmap-ollama" --format "{{.Names}}" 2>&1
if ($ollamaRunning -ne "pdf-mindmap-ollama") {
    Write-Host "Error: Ollama container is not running. Start services first with: .\scripts\start.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "This may take several minutes depending on your internet connection..." -ForegroundColor Yellow
Write-Host ""

# Pull the model
docker exec -it pdf-mindmap-ollama ollama pull $Model

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Model '$Model' pulled successfully!" -ForegroundColor Green
    Write-Host "You can now use the PDF Mind Map Generator." -ForegroundColor Cyan
} else {
    Write-Host "Error pulling model. Check your internet connection and try again." -ForegroundColor Red
    exit 1
}
