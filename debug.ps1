# Debug Script for Bose Product Engine
# Checks system health and displays diagnostic information

Write-Host "=== Bose Product Engine Debug Information ===" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Python Version:" -ForegroundColor Yellow
python --version
Write-Host ""

# Check if venv is activated
Write-Host "Virtual Environment:" -ForegroundColor Yellow
if ($env:VIRTUAL_ENV) {
    Write-Host "✓ Active: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "✗ Not activated. Run: .\venv\Scripts\Activate.ps1" -ForegroundColor Red
}
Write-Host ""

# Check PostgreSQL
Write-Host "PostgreSQL Status:" -ForegroundColor Yellow
$pgContainer = docker ps --filter "name=bose-postgres" --format "{{.Status}}"
if ($pgContainer) {
    Write-Host "✓ Running: $pgContainer" -ForegroundColor Green
    
    # Check database
    Write-Host "  Product count:" -ForegroundColor Yellow
    docker exec bose-postgres psql -U postgres -d bose_products -t -c "SELECT COUNT(*) FROM products;"
} else {
    Write-Host "✗ Not running" -ForegroundColor Red
}
Write-Host ""

# Check Ollama
Write-Host "Ollama Status:" -ForegroundColor Yellow
try {
    $ollamaModels = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -ErrorAction Stop
    Write-Host "✓ Running" -ForegroundColor Green
    Write-Host "  Available models:" -ForegroundColor Yellow
    $ollamaModels.models | ForEach-Object { Write-Host "    - $($_.name)" }
} catch {
    Write-Host "✗ Not running or not accessible" -ForegroundColor Red
}
Write-Host ""

# Check for required files
Write-Host "Required Files:" -ForegroundColor Yellow
$files = @(".env", "db/schema.sql", "data/pdfs/Bose-Products 3.pdf")
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file (missing)" -ForegroundColor Red
    }
}
Write-Host ""

# Check port availability
Write-Host "Port Status:" -ForegroundColor Yellow
$ports = @(8000, 5433, 11434)
foreach ($port in $ports) {
    $listener = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener) {
        Write-Host "  Port $port : IN USE (PID: $($listener[0].OwningProcess))" -ForegroundColor Yellow
    } else {
        Write-Host "  Port $port : Available" -ForegroundColor Green
    }
}
Write-Host ""

# Check installed packages
Write-Host "Key Python Packages:" -ForegroundColor Yellow
$packages = @("fastmcp", "asyncpg", "httpx", "pypdf")
foreach ($pkg in $packages) {
    $installed = pip show $pkg 2>$null
    if ($installed) {
        $version = ($installed | Select-String "Version:").ToString().Split(":")[1].Trim()
        Write-Host "  ✓ $pkg ($version)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $pkg (not installed)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Debug Complete ===" -ForegroundColor Cyan
