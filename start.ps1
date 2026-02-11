# Quick Start Script for Bose Product Engine
# Run this after initial setup is complete

Write-Host "Starting Bose Product Engine..." -ForegroundColor Green

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Start PostgreSQL
Write-Host "Starting PostgreSQL..." -ForegroundColor Yellow
docker-compose up -d postgres
Start-Sleep -Seconds 3

# Verify PostgreSQL is running
$pgRunning = docker ps | Select-String "bose-postgres"
if ($pgRunning) {
    Write-Host "✓ PostgreSQL is running" -ForegroundColor Green
} else {
    Write-Host "✗ PostgreSQL failed to start" -ForegroundColor Red
    exit 1
}

# Check if Ollama is running
Write-Host "Checking Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -ErrorAction Stop
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Ollama is not running. Please start Ollama first." -ForegroundColor Red
    Write-Host "  Run: ollama serve" -ForegroundColor Yellow
    exit 1
}

# Start MCP Server
Write-Host "Starting MCP Server on port 8000..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Cyan
python -m src.server.main
