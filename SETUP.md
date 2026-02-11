# Bose Product Engine - Setup Guide

Complete guide to set up and run the Bose Product RAG Query Engine.

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** (via Docker recommended)
- **Ollama** (for embeddings and LLM)

---

## 1. Initial Setup

### Create Virtual Environment

```powershell
# Navigate to project directory
cd "d:\production local RAG"

# Create venv
python -m venv venv

# Activate venv
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install project dependencies
pip install -e .

# Or install from requirements if available
pip install -r requirements.txt
```

---

## 2. Environment Configuration

### Create `.env` File

```powershell
# Copy example
cp .env.example .env

# Edit .env with your settings
notepad .env
```

**Required `.env` variables:**
```ini
# Database
DB_HOST=localhost
DB_PORT=5433
DB_NAME=bose_products
DB_USER=postgres
DB_PASSWORD=postgres

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=bge-m3
OLLAMA_LLM_MODEL=llama3.2:3b

# Embedding
EMBEDDING_DIMENSION=1024

# Paths
PDF_DIR=./data/pdfs
CACHE_DIR=./data/cache
```

---

## 3. Start Infrastructure

### Start PostgreSQL (Docker)

```powershell
# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Verify it's running
docker ps

# Check logs if needed
docker logs bose-postgres
```

### Initialize Database Schema

```powershell
# Run schema creation
docker exec -i bose-postgres psql -U postgres -d bose_products < db/schema.sql

# Or connect and run manually
docker exec -it bose-postgres psql -U postgres -d bose_products
```

### Start Ollama

```powershell
# Start Ollama (if not already running)
ollama serve

# In another terminal, pull required models
ollama pull bge-m3
ollama pull llama3.2:3b
```

---

## 4. Run ETL Pipeline

### Extract, Transform, Load Product Data

```powershell
# Run full ETL pipeline
python -m src.etl.pipeline

# Expected output:
# - Extracted tables from PDF
# - Normalized 86 products
# - Loaded to database with embeddings
# - Takes ~5-10 minutes
```

### Verify ETL Results

```powershell
# Check database contents
python check_db.py

# Expected: 86 products loaded
```

---

## 5. Test the System

### Run Query Engine Tests

```powershell
# Test all query types
python test_query_engine.py

# Test liability prevention (Phase 4)
python test_defense.py
```

---

## 6. Run MCP Server

### Start the MCP Server

```powershell
# Default port (8000)
python -m src.server.main

# Custom port
python -m src.server.main --port 8001

# Expected output:
# - FastMCP banner
# - Server running on http://0.0.0.0:8000/sse
```

### Test MCP Client

```powershell
# In another terminal (with venv activated)
python test_mcp_client.py
```

---

## 7. Debugging Commands

### Database Debugging

```powershell
# Connect to database
docker exec -it bose-postgres psql -U postgres -d bose_products

# Useful queries:
# SELECT COUNT(*) FROM products;
# SELECT model_name, category, series FROM products LIMIT 10;
# SELECT model_name, watts_int, voltage_type FROM products WHERE watts_int > 50;
```

### Check Ollama Status

```powershell
# List models
ollama list

# Test embedding
ollama run bge-m3 "test"

# Test LLM
ollama run llama3.2:3b "Hello"
```

### View Logs

```powershell
# PostgreSQL logs
docker logs -f bose-postgres

# Application logs (if running server)
# Logs appear in console by default
```

### Quick Health Checks

```powershell
# Check if PostgreSQL is accessible
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://postgres:postgres@localhost:5433/bose_products'))"

# Check if Ollama is accessible
curl http://localhost:11434/api/tags
```

### Reset Database (Nuclear Option)

```powershell
# Stop and remove container
docker-compose down -v

# Restart fresh
docker-compose up -d postgres

# Recreate schema
docker exec -i bose-postgres psql -U postgres -d bose_products < db/schema.sql

# Re-run ETL
python -m src.etl.pipeline
```

---

## 8. Common Issues

### Port Conflicts

```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill process by PID
taskkill /F /PID <PID>

# Or use a different port
python -m src.server.main --port 8002
```

### Database Connection Errors

```powershell
# Verify PostgreSQL is running
docker ps | findstr postgres

# Check connection
docker exec -it bose-postgres psql -U postgres -d bose_products -c "SELECT 1;"
```

### Ollama Not Responding

```powershell
# Restart Ollama
# Close Ollama app and restart, or:
taskkill /F /IM ollama.exe
ollama serve
```

### Import Errors

```powershell
# Reinstall in editable mode
pip install -e .

# Or add to PYTHONPATH
$env:PYTHONPATH = "d:\production local RAG"
```

---

## 9. Quick Start Script (All-in-One)

Save as `start.ps1`:

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Start PostgreSQL
docker-compose up -d postgres
Start-Sleep -Seconds 3

# Start Ollama (assumes it's already running)
# If not: Start-Process "ollama" -ArgumentList "serve"

# Run ETL if needed (uncomment for first run)
# python -m src.etl.pipeline

# Start MCP server
python -m src.server.main
```

Run with:
```powershell
.\start.ps1
```

---

## 10. Production Deployment Checklist

- [ ] Change default passwords in `.env`
- [ ] Use environment variables instead of `.env` file
- [ ] Enable SSL/TLS for PostgreSQL
- [ ] Configure firewall rules
- [ ] Set up monitoring and logging
- [ ] Configure backup for PostgreSQL
- [ ] Use production-grade WSGI server (if not using FastMCP's built-in)
- [ ] Set `LOG_LEVEL=INFO` or `WARNING`

---

## Next Steps

1. **Connect MCP Client**: Use Claude Desktop or Zed with `http://localhost:8000/sse`
2. **Test Queries**: Try technical questions, verify liability prevention works
3. **Customize**: Update `router.py` patterns, add more products via ETL

For more details, see `walkthrough.md`.
