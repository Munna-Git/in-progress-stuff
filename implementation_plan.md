# Phase 1: Database & ETL - Bose Professional Product Engine

## Overview

Building a local-first ETL pipeline to extract Bose professional audio equipment specs from PDFs and load them into PostgreSQL with pgvector for hybrid search capabilities.

**Key Constraints:**
- Local-only (No AWS, No Cloud APIs)
- asyncpg (NOT SQLAlchemy)
- docling (NOT Textract)
- Ollama bge-m3 for embeddings (384 dimensions)
- Target: <3 second query latency, <60 second ETL time

---

## Proposed Changes

### Docker Infrastructure

#### [NEW] [docker-compose.yml](file:///d:/production%20local%20RAG/docker-compose.yml)
- PostgreSQL 16 with pgvector image
- Persistent volume for data
- Health check configuration
- Auto-initialize schema on startup
- Network configuration for local development

---

### Database Schema

#### [NEW] [schema.sql](file:///d:/production%20local%20RAG/db/schema.sql)
- Enable pgvector extension
- `products` table with:
  - `model_name` (TEXT UNIQUE)
  - `specs` (JSONB for flexible storage)
  - Generated columns: `watts_int`, `category`, `voltage_type`
  - `embedding` (vector(384) for semantic search)
  - Source tracking: `pdf_source`, `page_number`
- Critical indexes for <3s queries:
  - B-tree on `watts_int`, `category`, `voltage_type`
  - GIN on `specs` JSONB
  - IVFFlat on `embedding` for vector search

---

### Configuration Layer

#### [NEW] [.env.example](file:///d:/production%20local%20RAG/.env.example)
- Database connection settings
- Ollama configuration (host, models)
- ETL settings (batch size, cache options)
- Performance tuning parameters

#### [NEW] [config.py](file:///d:/production%20local%20RAG/src/config.py)
- Pydantic Settings for type-safe configuration
- Load from .env file
- Validation for required fields
- Default values for optional settings

---

### Database Connection

#### [NEW] [database.py](file:///d:/production%20local%20RAG/src/database.py)
- asyncpg connection pool manager
- Context manager for safe connection handling
- Pool configuration (min/max connections)
- Health check and reconnection logic
- Async context manager pattern

---

### ETL Pipeline Components

#### [NEW] [extractor.py](file:///d:/production%20local%20RAG/src/etl/extractor.py)
- docling PDF table extraction
- **Header Propagation Logic**: Handle merged cells by forward-filling headers
- Create hierarchical column names (e.g., `Driver_Components_LF`)
- Cache raw extraction results to JSON
- Comprehensive error handling and logging

#### [NEW] [normalizer.py](file:///d:/production%20local%20RAG/src/etl/normalizer.py)
- **Row Explosion**: Split `AM10/60/80` → `AM10/60`, `AM10/80`
- **Unit Parsing**:
  - Power: `"125 W"` → `125`
  - Frequency: `"95 Hz - 16 kHz"` → `{"min": 95, "max": 16000}`
  - Impedance: `"8 ohms"` → `8`
  - Voltage: `"70V/100V"` → `"70V"`
- Validation and data quality checks
- Cache normalized output to JSON

#### [NEW] [synthesizer.py](file:///d:/production%20local%20RAG/src/etl/synthesizer.py)
- Ollama llama3.2:3b client for summarization
- Generate product summaries for better semantic search
- Async HTTP client (httpx)
- Rate limiting and retry logic
- Error handling for LLM failures

#### [NEW] [loader.py](file:///d:/production%20local%20RAG/src/etl/loader.py)
- Ollama bge-m3 embedding generation
- **Embedding caching** to avoid regeneration
- Batch insert with UPSERT conflict handling
- asyncpg bulk insert operations
- Transaction management

#### [NEW] [pipeline.py](file:///d:/production%20local%20RAG/src/etl/pipeline.py)
- Main orchestrator for ETL workflow
- Sequential execution: Extract → Normalize → Synthesize → Load
- Progress logging and timing
- Error aggregation and reporting
- CLI interface for running pipeline

---

### Supporting Files

#### [NEW] [pyproject.toml](file:///d:/production%20local%20RAG/pyproject.toml)
Core dependencies:
- `docling>=1.0.0` - PDF extraction
- `asyncpg>=0.29.0` - Async PostgreSQL
- `httpx>=0.25.0` - Ollama API client
- `pydantic-settings>=2.0.0` - Configuration
- `numpy>=1.24.0` - Vector operations
- `pandas>=2.0.0` - Data manipulation

Dev dependencies:
- `pytest`, `pytest-asyncio` - Testing
- `black`, `ruff` - Linting

---

## Verification Plan

### Automated Tests

1. **Docker Container Test**
   ```powershell
   # Start PostgreSQL container
   docker compose up -d
   
   # Wait for health check
   docker compose ps
   
   # Verify connection
   docker exec bose_postgres psql -U bose_admin -d bose_products -c "\dt"
   ```

2. **Schema Validation**
   ```powershell
   # Verify tables and indexes exist
   docker exec bose_postgres psql -U bose_admin -d bose_products -c "\dt"
   docker exec bose_postgres psql -U bose_admin -d bose_products -c "\di"
   ```

3. **ETL Pipeline Test**
   ```powershell
   # Install dependencies
   pip install -e .
   
   # Run pipeline
   python -m src.etl.pipeline
   
   # Verify products in database
   docker exec bose_postgres psql -U bose_admin -d bose_products -c "SELECT COUNT(*) FROM products"
   ```

### Manual Verification

1. **Check Ollama Models** (requires Ollama installed):
   ```powershell
   ollama list
   # Should show: bge-m3, llama3.2:3b
   ```

2. **Verify Embeddings**:
   ```sql
   -- Run in psql
   SELECT model_name, array_length(embedding::float[], 1) as dims 
   FROM products 
   LIMIT 5;
   -- Should show dims = 384
   ```

3. **Test Query Performance**:
   ```sql
   EXPLAIN ANALYZE 
   SELECT * FROM products 
   WHERE watts_int > 50 AND voltage_type = '70V' 
   LIMIT 10;
   -- Should complete in <100ms
   ```

> [!NOTE]
> User must have Docker Desktop and Ollama installed locally. The PDF file `Bose-Products 3.pdf` should be placed in `data/raw_pdfs/` before running the ETL pipeline.

---

## Success Criteria

- [ ] Docker PostgreSQL running on port 5432
- [ ] pgvector extension enabled
- [ ] All indexes created
- [ ] 5 PDF pages processed in <60 seconds
- [ ] Products loaded with 384-dimension embeddings
- [ ] Cache files exist in `data/processed/`
- [ ] Zero errors in pipeline logs
