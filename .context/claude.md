# Bose Professional Product Engine - Context

## Project Overview
Zero-hallucination product search system for Bose professional audio equipment.
100% Local-First architecture (No AWS, No Cloud APIs).

## Critical Constraints
- Use asyncpg (NOT SQLAlchemy)
- Use docling (NOT Textract)
- Use Ollama bge-m3 for embeddings (384 dimensions)
- Use Ollama llama3.2:3b for LLM
- Target: <3 second query latency

## Phase 1: Database & ETL (Complete)
- PostgreSQL 16 + pgvector (docker-compose.yml)
- Schema with generated columns (db/schema.sql)
- asyncpg connection pool (src/database.py)
- ETL Pipeline: Extract → Normalize → Synthesize → Load

## Key Features
- Header propagation for merged PDF cells
- Row explosion for model ranges (AM10/60/80 → AM10/60, AM10/80)
- Unit parsing: "125 W" → 125, "95 Hz - 16 kHz" → {min: 95, max: 16000}
- Embedding caching to avoid regeneration

## Quick Commands
```bash
# Start database
docker compose up -d

# Run ETL
python -m src.etl.pipeline

# Check products
docker exec bose_postgres psql -U bose_admin -d bose_products -c "SELECT model_name, category, watts_int FROM products"
```
