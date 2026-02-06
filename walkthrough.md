# Phase 1 Walkthrough - Database & ETL

## Summary
Created complete Phase 1 infrastructure for the Bose Professional Product Engine with PostgreSQL + pgvector and a full ETL pipeline.

---

## Files Created

### Infrastructure
| File | Purpose |
|------|---------|
| [docker-compose.yml](file:///d:/production%20local%20RAG/docker-compose.yml) | PostgreSQL 16 + pgvector container |
| [db/schema.sql](file:///d:/production%20local%20RAG/db/schema.sql) | Schema with generated columns + indexes |
| [.env](file:///d:/production%20local%20RAG/.env) | Configuration settings |

### Core Modules
| File | Purpose |
|------|---------|
| [src/config.py](file:///d:/production%20local%20RAG/src/config.py) | Pydantic settings from .env |
| [src/database.py](file:///d:/production%20local%20RAG/src/database.py) | asyncpg connection pool + pgvector support |

### ETL Pipeline
| File | Purpose |
|------|---------|
| [src/etl/extractor.py](file:///d:/production%20local%20RAG/src/etl/extractor.py) | docling PDF extraction + header propagation |
| [src/etl/normalizer.py](file:///d:/production%20local%20RAG/src/etl/normalizer.py) | Row explosion + unit parsing |
| [src/etl/synthesizer.py](file:///d:/production%20local%20RAG/src/etl/synthesizer.py) | Ollama summarization |
| [src/etl/loader.py](file:///d:/production%20local%20RAG/src/etl/loader.py) | Embeddings + batch insert |
| [src/etl/pipeline.py](file:///d:/production%20local%20RAG/src/etl/pipeline.py) | Main orchestrator with CLI |

---

## Key Features Implemented

### Header Propagation
Handles merged PDF cells by forward-filling values and creating hierarchical column names:
```
| Driver Components (spans 3 cols) |  →  Driver_Components_LF, Driver_Components_MF, Driver_Components_HF
```

### Row Explosion
Splits model ranges into individual products:
```
AM10/60/80 → AM10/60, AM10/80
```

### Unit Parsing
Extracts structured data from text:
- `"125 W"` → `power_watts: 125`
- `"95 Hz - 16 kHz"` → `freq_min_hz: 95, freq_max_hz: 16000`
- `"8 ohms"` → `impedance_ohms: 8`

### Generated Columns
Fast SQL filtering without parsing JSONB:
```sql
WHERE watts_int > 100 AND voltage_type = '70V'
```

---

## Next Steps to Verify

```powershell
# 1. Start PostgreSQL
docker compose up -d

# 2. Install dependencies
pip install -e .

# 3. Pull Ollama models
ollama pull bge-m3
ollama pull llama3.2:3b

# 4. Run ETL pipeline
python -m src.etl.pipeline

# 5. Check database
docker exec bose_postgres psql -U bose_admin -d bose_products -c "SELECT model_name, category, watts_int FROM products LIMIT 10"
```
