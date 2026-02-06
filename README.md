# Bose Professional Product Engine

Zero-hallucination product search system for Bose professional audio equipment specifications.

## 🚀 Quick Start

### Prerequisites

1. **Docker Desktop** - For PostgreSQL with pgvector
2. **Ollama** - For local embeddings and LLM
3. **Python 3.11+**

### Setup

```bash
# 1. Clone and enter directory
cd bose-product-engine

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -e .

# 4. Start PostgreSQL
docker compose up -d

# 5. Start Ollama and pull models
ollama pull bge-m3
ollama pull llama3.2:3b

# 6. Copy your PDF to data directory
copy "Bose-Products 3.pdf" data\raw_pdfs\

# 7. Run ETL pipeline
python -m src.etl.pipeline
```

## 📁 Project Structure

```
bose-product-engine/
├── docker-compose.yml      # PostgreSQL + pgvector
├── db/schema.sql           # Database schema
├── .env                    # Configuration
├── pyproject.toml          # Dependencies
│
├── data/
│   ├── raw_pdfs/           # Drop PDFs here
│   └── processed/          # JSON cache files
│
└── src/
    ├── config.py           # Pydantic settings
    ├── database.py         # asyncpg pool manager
    └── etl/
        ├── extractor.py    # docling PDF extraction
        ├── normalizer.py   # Row explosion + unit parsing
        ├── synthesizer.py  # Ollama summarization
        ├── loader.py       # DB insert + embeddings
        └── pipeline.py     # Main orchestrator
```

## 🔧 Configuration

Edit `.env` file:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=bose_admin
POSTGRES_PASSWORD=local_dev_pass
POSTGRES_DB=bose_products

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_LLM_MODEL=llama3.2:3b

# ETL
BATCH_SIZE=10
CACHE_EMBEDDINGS=true
```

## 🛠️ ETL Pipeline

The pipeline processes Bose product PDFs in 4 stages:

1. **Extract** - Parse tables from PDFs using docling with header propagation
2. **Normalize** - Explode model ranges (AM10/60/80 → AM10/60, AM10/80), parse units
3. **Synthesize** - Generate AI summaries for semantic search
4. **Load** - Insert into PostgreSQL with embeddings

```bash
# Run with default settings
python -m src.etl.pipeline

# Skip AI summaries
python -m src.etl.pipeline --skip-synthesis

# Custom PDF directory
python -m src.etl.pipeline --pdf-dir /path/to/pdfs

# Verbose logging
python -m src.etl.pipeline --log-level DEBUG
```

## 📊 Database Schema

Key features:
- **Generated columns** for fast filtering (`watts_int`, `category`, `voltage_type`)
- **JSONB specs** for flexible storage
- **vector(384)** for semantic search with bge-m3 embeddings
- **IVFFlat index** for fast similarity search

```sql
-- Example queries
SELECT * FROM products WHERE watts_int > 100;
SELECT * FROM products WHERE voltage_type = '70V';
SELECT * FROM products ORDER BY embedding <=> $1 LIMIT 10;
```

## 🐳 Docker Commands

```bash
# Start PostgreSQL
docker compose up -d

# View logs
docker compose logs -f postgres

# Connect to database
docker exec -it bose_postgres psql -U bose_admin -d bose_products

# Stop
docker compose down

# Stop and remove data
docker compose down -v
```

## ⚡ Performance Targets

- ETL: <60 seconds for 5 PDF pages
- Query latency: <3 seconds
- Embedding dimension: 384 (bge-m3)

## 📋 Requirements

**Critical Constraints:**
- ❌ NO AWS Services
- ❌ NO Cloud APIs
- ❌ NO SQLAlchemy
- ✅ 100% Local-First

**Stack:**
- PostgreSQL 16 + pgvector
- asyncpg (async database)
- docling (PDF extraction)
- Ollama (embeddings + LLM)
- Pydantic (configuration)
"# in-progress-stuff" 
