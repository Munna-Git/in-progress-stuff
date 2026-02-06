# 🎯 CLAUDE CODE COMMAND PACKET
## Bose Professional Product Engine - Local Demo

---

## 📋 PROJECT OVERVIEW

**Project Name:** Bose Professional Product Engine (Local Demo)  
**Objective:** Zero-hallucination product search system for Bose audio equipment specifications  
**Target Hardware:** Dell Laptop (Intel Core Ultra 5, 16GB RAM)  
**Performance Target:** <5 second query latency  
**Accuracy Target:** 95%+ on golden test set  
**Architecture:** 100% Local-First (No Cloud Dependencies)

---

## 🚨 CRITICAL CONSTRAINTS

### ❌ WHAT NOT TO USE
- **NO AWS Services** (No Textract, No Bedrock, No RDS)
- **NO Cloud APIs** (No Voyage, No Anthropic API, No OpenAI)
- **NO SQLAlchemy ORM** (Use asyncpg for performance)
- **NO External Vector Databases** (Use PostgreSQL pgvector)

### ✅ WHAT TO USE
- **PDF Extraction:** docling (local Python library)
- **Embeddings:** Ollama bge-m3 (384 dimensions, local)
- **LLM:** Ollama llama3.2:3b (quantized, local)
- **Database:** PostgreSQL 16 + pgvector (Docker)
- **Async DB:** asyncpg (not psycopg2)
- **Server:** FastMCP (Model Context Protocol)

---

## 📁 PROJECT STRUCTURE

```
bose-product-engine/
│
├── .context/
│   └── claude.md                    # YOU MUST READ THIS FIRST
│
├── .env.example                     # Configuration template
├── .gitignore
├── docker-compose.yml               # PostgreSQL 16 + pgvector
├── pyproject.toml                   # Python dependencies
├── README.md
│
├── db/
│   └── schema.sql                   # Database schema with indexes
│
├── data/
│   ├── raw_pdfs/                    # User drops PDFs here
│   └── processed/                   # JSON cache directory
│       ├── raw_tables.json          # docling output
│       ├── normalized_products.json # After normalization
│       └── embeddings_cache.json    # Ollama embeddings cache
│
├── src/
│   ├── __init__.py
│   ├── config.py                    # Pydantic settings from .env
│   ├── database.py                  # asyncpg connection manager
│   │
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── pipeline.py              # Main ETL orchestrator
│   │   ├── extractor.py             # docling PDF extraction
│   │   ├── normalizer.py            # Row explosion + unit parsing
│   │   ├── synthesizer.py           # Ollama summarization
│   │   └── loader.py                # PostgreSQL insert with embeddings
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embeddings.py            # Ollama embedding client
│   │   ├── router.py                # Intent classifier
│   │   ├── retrieval.py             # Hybrid SQL + vector search
│   │   └── generator.py             # Answer with citations
│   │
│   ├── logic/
│   │   ├── __init__.py
│   │   └── calculator.py            # Deterministic electrical math
│   │
│   └── server/
│       ├── __init__.py
│       ├── main.py                  # FastMCP server
│       └── tools.py                 # MCP tool definitions
│
├── scripts/
│   ├── setup.py                     # One-click setup
│   └── evaluate.py                  # Accuracy evaluation
│
├── tests/
│   ├── test_etl.py                  # ETL tests
│   ├── test_retrieval.py            # Retrieval tests
│   ├── golden_set.json              # 20-30 Q&A validation pairs
│   └── run_accuracy.py              # Automated accuracy check
│
└── docs/
    └── SETUP.md                     # Setup instructions
```

---

## 🎯 UNIQUE TECHNICAL CHALLENGES

### Challenge 1: Merged Header Cells in PDFs
**Problem:**
```
| Driver Components (spans 3 cols) | Acoustics      |
| LF      | MF      | HF      | Freq Range |
| 8"      | 1.5"    | 0.75"   | 95Hz-16kHz |
```

**Solution Required:**
- Use docling to extract tables
- Implement "Header Propagation" logic:
  - Forward-fill merged headers across columns
  - Create hierarchical column names: `Driver_Components_LF`, `Driver_Components_MF`, `Driver_Components_HF`
- Store in JSONB with clean structure

**Implementation Location:** `src/etl/extractor.py`

---

### Challenge 2: Model Range Explosion
**Problem:**
- Single PDF row: `AM10/60/80` represents 2 distinct models
- Each model has different specifications

**Solution Required:**
- Detect pattern: `BASE/VARIANT1/VARIANT2`
- Split into separate database rows:
  - `AM10/60` with its specs
  - `AM10/80` with its specs
- Preserve all other specifications for each model

**Implementation Location:** `src/etl/normalizer.py`

**Code Pattern:**
```python
def explode_model_ranges(model_str: str) -> list[str]:
    """
    Input: "AM10/60/80"
    Output: ["AM10/60", "AM10/80"]
    """
    # Regex: ([A-Z]+\d+)/(.+)
    # Split variants and reconstruct
```

---

### Challenge 3: Unit Normalization
**Problem:**
Mixed formats in PDF:
- "125 W" → Need integer 125
- "95 Hz - 16 kHz" → Need {"min": 95, "max": 16000}
- "8 ohms" → Need integer 8
- "70V/100V" → Need "70V" category

**Solution Required:**
Regex patterns for each unit type:
```python
# Power: (\d+)\s*W → integer
# Frequency: (\d+)\s*Hz\s*-\s*(\d+)\s*kHz → {min, max}
# Impedance: (\d+)\s*ohms? → integer
# Voltage: (70V|100V) → category string
```

**Implementation Location:** `src/etl/normalizer.py`

---

### Challenge 4: Hybrid Search Performance
**Problem:** 
Need both exact filtering AND semantic search in <5 seconds

**Solution Required:**
Two-stage retrieval:
1. **Hard Filtering (SQL):** `WHERE watts_int > 50 AND voltage_type = '70V'`
2. **Soft Reranking (Vector):** Order by cosine similarity

**Implementation Location:** `src/rag/retrieval.py`

**Code Pattern:**
```python
async def hybrid_search(query: str, filters: dict) -> list:
    # Stage 1: SQL WHERE clause
    candidates = await db.fetch("""
        SELECT * FROM products 
        WHERE watts_int > $1 AND voltage_type = $2
        LIMIT 50
    """, filters['min_watts'], filters['voltage'])
    
    # Stage 2: Vector rerank
    query_embedding = await get_embedding(query)
    reranked = rank_by_similarity(candidates, query_embedding)
    return reranked[:10]
```

---

## 🗄️ DATABASE SCHEMA REQUIREMENTS

### Table: `products`
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    model_name TEXT UNIQUE NOT NULL,
    specs JSONB NOT NULL,
    
    -- Generated columns for fast filtering (CRITICAL)
    watts_int INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN specs->>'power_watts' IS NOT NULL 
            THEN (specs->>'power_watts')::INTEGER 
            ELSE NULL 
        END
    ) STORED,
    
    category TEXT GENERATED ALWAYS AS (
        specs->>'category'
    ) STORED,
    
    voltage_type TEXT GENERATED ALWAYS AS (
        specs->>'voltage_type'  -- '70V', '100V', 'Low-Z'
    ) STORED,
    
    -- Vector for semantic search (384 dimensions = bge-m3)
    embedding vector(384),
    
    -- Metadata
    pdf_source TEXT,
    page_number INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- CRITICAL INDEXES (Required for <5s queries)
CREATE INDEX idx_watts ON products(watts_int) WHERE watts_int IS NOT NULL;
CREATE INDEX idx_category ON products(category);
CREATE INDEX idx_voltage ON products(voltage_type);
CREATE INDEX idx_specs_gin ON products USING GIN(specs);
CREATE INDEX idx_embedding ON products USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
```

**File Location:** `db/schema.sql`

---

## ⚙️ CONFIGURATION (.env)

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=bose_admin
POSTGRES_PASSWORD=local_dev_pass
POSTGRES_DB=bose_products

# Ollama (Local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_LLM_MODEL=llama3.2:3b

# ETL Settings
MAX_PDF_PAGES=5
BATCH_SIZE=10
CACHE_EMBEDDINGS=true

# Performance
QUERY_TIMEOUT_SECONDS=5
MAX_DB_CONNECTIONS=10
EMBEDDING_DIMENSION=384
```

**File Location:** `.env.example`

---

## 📦 DEPENDENCIES (pyproject.toml)

```toml
[project]
name = "bose-product-engine"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "docling>=1.0.0",           # Local PDF extraction
    "pandas>=2.0.0",            # Data manipulation
    "asyncpg>=0.29.0",          # Async PostgreSQL (NOT psycopg2)
    "httpx>=0.25.0",            # Ollama API client
    "pydantic-settings>=2.0.0", # Config management
    "fastmcp>=0.1.0",           # MCP server framework
    "numpy>=1.24.0",            # Vector operations
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]
```

**Critical:** NO boto3, NO voyageai, NO anthropic SDK

---

## 🔄 ETL PIPELINE FLOW

```
┌─────────────┐
│  Bose PDF   │ (5 pages max)
│ (raw_pdfs/) │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  extractor.py   │ ← Uses docling
│  • Parse tables │
│  • Merge headers│
│  • Cache JSON   │
└────────┬────────┘
         │ raw_tables.json
         ▼
┌─────────────────┐
│ normalizer.py   │
│  • Row explosion│ (AM10/60/80 → 2 rows)
│  • Unit parsing │ ("125 W" → 125)
│  • Validation   │
└────────┬────────┘
         │ normalized_products.json
         ▼
┌─────────────────┐
│ synthesizer.py  │ ← Ollama llama3.2:3b
│  • Generate     │
│    summaries    │
└────────┬────────┘
         │ + ai_summary field
         ▼
┌─────────────────┐
│   loader.py     │ ← Ollama bge-m3 + asyncpg
│  • Get embedding│
│  • Insert to DB │
│  • Batch 10x    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  + pgvector     │
│  Ready for      │
│  queries!       │
└─────────────────┘
```

**Target Time:** <60 seconds for 5 pages

---

## 🔍 QUERY ROUTING LOGIC

### Intent Classification (router.py)

```python
# Uses Ollama llama3.2:3b locally
classify_query(user_query) → QueryType

QueryType Options:
1. DIRECT_LOOKUP    # "What's the power of AM10/60?"
2. SEMANTIC_SEARCH  # "Find ceiling speakers for conference rooms"
3. CALCULATION      # "Can I connect 8 speakers to 70V?"
```

### Routing Decision Tree

```
User Query
    │
    ▼
┌─────────────────┐
│  router.py      │ ← Ollama classification
│  Classify intent│
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬──────────────┐
    │         │             │              │
    ▼         ▼             ▼              ▼
DIRECT    SEMANTIC    CALCULATION      UNKNOWN
LOOKUP    SEARCH                       (error)
    │         │             │
    ▼         ▼             ▼
  SQL      SQL +        calculator.py
 WHERE   pgvector       (pure Python)
          rerank
```

**Example Queries:**

| Query | Type | Execution |
|-------|------|-----------|
| "What's the impedance of AM10/60?" | DIRECT_LOOKUP | `SELECT specs FROM products WHERE model_name = 'AM10/60'` |
| "Find 70V speakers over 100W" | SEMANTIC_SEARCH | SQL filter + vector rerank |
| "Can I connect 4x 30W speakers to 150W transformer?" | CALCULATION | `calculator.py` (deterministic) |

---

## 🧮 DETERMINISTIC CALCULATOR

**File:** `src/logic/calculator.py`

**Critical Rule:** NO LLM for electrical calculations

**Required Functions:**

```python
class ElectricalCalculator:
    @staticmethod
    def calculate_total_power(speakers: list[int]) -> int:
        """Sum wattages: [30, 30, 25, 25] → 110W"""
        return sum(speakers)
    
    @staticmethod
    def verify_70v_compatibility(
        total_watts: int, 
        transformer_watts: int
    ) -> dict:
        """
        Returns:
        {
            "compatible": bool,
            "total_load": int,
            "capacity": int,
            "headroom_percent": float
        }
        """
        compatible = total_watts <= transformer_watts
        headroom = ((transformer_watts - total_watts) / transformer_watts) * 100
        return {
            "compatible": compatible,
            "total_load": total_watts,
            "capacity": transformer_watts,
            "headroom_percent": round(headroom, 1)
        }
    
    @staticmethod
    def calculate_impedance(
        speakers: list[float], 
        connection: str
    ) -> float:
        """
        connection: 'series' or 'parallel'
        speakers: [8, 8, 8] ohms
        """
        if connection == 'series':
            return sum(speakers)
        elif connection == 'parallel':
            return 1 / sum(1/z for z in speakers)
        else:
            raise ValueError("connection must be 'series' or 'parallel'")
```

---

## 🧪 TESTING REQUIREMENTS

### Golden Test Set (tests/golden_set.json)

**Format:**
```json
[
  {
    "id": 1,
    "query": "What's the power rating of AM10/60?",
    "expected_answer": "125 watts",
    "expected_model": "AM10/60",
    "query_type": "DIRECT_LOOKUP",
    "acceptable_variations": ["125W", "125 W"]
  },
  {
    "id": 2,
    "query": "Find ceiling speakers for conference rooms",
    "expected_models": ["DesignMax DM3C", "EdgeMax EM90"],
    "query_type": "SEMANTIC_SEARCH",
    "min_results": 2
  },
  {
    "id": 3,
    "query": "Can I connect 4 speakers at 30W each to a 150W 70V transformer?",
    "expected_answer": "Yes",
    "expected_calculation": {
      "total_load": 120,
      "capacity": 150,
      "compatible": true
    },
    "query_type": "CALCULATION"
  }
]
```

**Requirement:** Minimum 20 test cases covering:
- 8 DIRECT_LOOKUP queries
- 8 SEMANTIC_SEARCH queries
- 4 CALCULATION queries

### Accuracy Calculation (tests/run_accuracy.py)

```python
def evaluate_accuracy(golden_set: list, engine) -> float:
    correct = 0
    for test_case in golden_set:
        result = engine.query(test_case["query"])
        if verify_answer(result, test_case):
            correct += 1
    
    accuracy = (correct / len(golden_set)) * 100
    return accuracy

# PASS CRITERIA: accuracy >= 95.0
```

---

## 🚀 IMPLEMENTATION PHASES

### PHASE 1: Database & ETL (Priority: CRITICAL)
**Files to Generate:**
1. ✅ `docker-compose.yml` - PostgreSQL + pgvector setup
2. ✅ `db/schema.sql` - Complete schema with indexes
3. ✅ `src/config.py` - Pydantic settings
4. ✅ `src/database.py` - asyncpg connection manager
5. ✅ `src/etl/extractor.py` - docling extraction + header propagation
6. ✅ `src/etl/normalizer.py` - Row explosion + unit parsing
7. ✅ `src/etl/synthesizer.py` - Ollama summarization
8. ✅ `src/etl/loader.py` - DB insertion with embeddings
9. ✅ `src/etl/pipeline.py` - Orchestrator

**Success Criteria:**
- [ ] 5 PDF pages processed in <60 seconds
- [ ] 30+ products in database
- [ ] All embeddings cached
- [ ] Zero errors in logs

---

### PHASE 2: RAG System (Priority: HIGH)
**Files to Generate:**
10. ✅ `src/rag/embeddings.py` - Ollama embedding client
11. ✅ `src/rag/router.py` - Intent classifier
12. ✅ `src/rag/retrieval.py` - Hybrid search
13. ✅ `src/rag/generator.py` - Answer generation
14. ✅ `src/logic/calculator.py` - Electrical math

**Success Criteria:**
- [ ] Query classification accuracy >90%
- [ ] Hybrid search returns results in <3s
- [ ] Calculator gives exact answers (0% error)

---

### PHASE 3: Server & Testing (Priority: MEDIUM)
**Files to Generate:**
15. ✅ `src/server/main.py` - FastMCP server
16. ✅ `src/server/tools.py` - MCP tool definitions
17. ✅ `tests/golden_set.json` - 20+ test cases
18. ✅ `tests/run_accuracy.py` - Automated evaluation
19. ✅ `scripts/setup.py` - One-click setup
20. ✅ `scripts/evaluate.py` - Manual testing script

**Success Criteria:**
- [ ] MCP server responds in <5s
- [ ] Golden set accuracy ≥95%
- [ ] Setup script works on fresh laptop

---

## 🔧 DOCKER COMPOSE TEMPLATE

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: bose_postgres
    environment:
      POSTGRES_USER: bose_admin
      POSTGRES_PASSWORD: local_dev_pass
      POSTGRES_DB: bose_products
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bose_admin -d bose_products"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - bose_network

volumes:
  postgres_data:
    driver: local

networks:
  bose_network:
    driver: bridge
```

**Usage:**
```bash
docker compose up -d
docker compose logs -f postgres
```

---

## 📝 KEY IMPLEMENTATION NOTES

### 1. Ollama API Endpoints
```python
# Embedding generation
POST http://localhost:11434/api/embeddings
{
  "model": "bge-m3",
  "prompt": "AM10/60 ceiling speaker 125W"
}

# LLM generation
POST http://localhost:11434/api/generate
{
  "model": "llama3.2:3b",
  "prompt": "Classify this query: Find 70V speakers",
  "stream": false
}
```

### 2. asyncpg Connection Pattern
```python
import asyncpg

async def get_connection():
    return await asyncpg.connect(
        host='localhost',
        port=5432,
        user='bose_admin',
        password='local_dev_pass',
        database='bose_products'
    )

# Always use async context manager
async with get_connection() as conn:
    result = await conn.fetch("SELECT * FROM products")
```

### 3. Embedding Caching Strategy
```python
# Check cache first
cache_path = "data/processed/embeddings_cache.json"
if os.path.exists(cache_path):
    with open(cache_path) as f:
        cache = json.load(f)
    if text in cache:
        return cache[text]

# Generate and cache
embedding = await generate_embedding(text)
cache[text] = embedding
with open(cache_path, 'w') as f:
    json.dump(cache, f)
```

### 4. Error Handling Pattern
```python
import logging

logger = logging.getLogger(__name__)

try:
    result = await process_pdf(pdf_path)
except Exception as e:
    logger.error(f"PDF processing failed: {e}", exc_info=True)
    # Continue with next file, don't crash
    return {"status": "failed", "error": str(e)}
```

---

## ✅ FINAL CHECKLIST

Before declaring Phase 1 complete:
- [ ] Docker PostgreSQL running on port 5432
- [ ] pgvector extension enabled
- [ ] All indexes created
- [ ] Ollama running with bge-m3 and llama3.2:3b models
- [ ] 5 PDF pages extracted successfully
- [ ] At least 30 products in database
- [ ] All products have embeddings (384 dimensions)
- [ ] Sample query returns results in <5 seconds
- [ ] No crash errors in logs
- [ ] Cache files exist in data/processed/

---

## 🎓 LEARNING RESOURCES

### docling Documentation
- Installation: `pip install docling`
- Usage: https://github.com/DS4SD/docling

### asyncpg Best Practices
- Connection pooling: Always use connection pools for production
- Transactions: Use `async with conn.transaction()`
- Type conversion: PostgreSQL types auto-convert to Python

### pgvector Queries
```sql
-- Find similar products
SELECT model_name, 
       1 - (embedding <=> $1) as similarity
FROM products
ORDER BY embedding <=> $1
LIMIT 10;
```

---

## 📞 SUPPORT & DEBUGGING

### Common Issues

**Issue:** "Cannot connect to PostgreSQL"
**Solution:** 
```bash
docker compose ps  # Check if running
docker compose logs postgres  # Check logs
```

**Issue:** "Ollama model not found"
**Solution:**
```bash
ollama list  # Check installed models
ollama pull bge-m3
ollama pull llama3.2:3b
```

**Issue:** "Embedding dimension mismatch"
**Solution:** Verify bge-m3 outputs 384 dimensions, not 768

**Issue:** "Query timeout >5s"
**Solution:** Check indexes exist, reduce LIMIT in queries

---

## 🎯 EXPECTED DELIVERABLES

After completing all phases, you will have:

1. ✅ **Working ETL Pipeline** - Process Bose PDFs in <60s
2. ✅ **Populated Database** - 30+ products with embeddings
3. ✅ **Query Engine** - <5s response time
4. ✅ **Deterministic Calculator** - Zero hallucination on math
5. ✅ **MCP Server** - Exposable via FastMCP
6. ✅ **Test Suite** - 95%+ accuracy on golden set
7. ✅ **Documentation** - Setup guide for fresh installation

---

## 🚦 START COMMAND FOR CLAUDE CODE

Copy and paste this into Claude Code Opus 4.5:

```
I need you to build Phase 1 (Database & ETL) of the Bose Professional Product Engine.

READ FIRST:
- Review the complete context in `.context/claude.md` (I'll upload it)
- This is a LOCAL-FIRST system (no AWS, no cloud APIs)
- Use asyncpg (NOT SQLAlchemy)
- Use docling (NOT Textract)
- Use Ollama (NOT Claude API or OpenAI)

PROJECT CONSTRAINTS:
- Target: <5 second query latency
- Hardware: Dell laptop, 16GB RAM
- Database: PostgreSQL 16 + pgvector (Docker)
- Embeddings: 384 dimensions (Ollama bge-m3)

GENERATE THESE FILES (in order):
1. docker-compose.yml - PostgreSQL setup
2. db/schema.sql - Complete schema with generated columns and indexes
3. src/config.py - Pydantic settings from .env
4. src/database.py - asyncpg connection manager with pooling
5. src/etl/extractor.py - docling extraction with header propagation logic
6. src/etl/normalizer.py - Row explosion (AM10/60/80 → 2 rows) + unit parsing
7. src/etl/synthesizer.py - Ollama summarization client
8. src/etl/loader.py - Batch insert with embedding generation
9. src/etl/pipeline.py - Main orchestrator

CRITICAL REQUIREMENTS:
- Header propagation for merged PDF cells
- Row explosion for model ranges (e.g., AM10/60/80)
- Unit parsing: "125 W" → 125, "95 Hz - 16 kHz" → {min: 95, max: 16000}
- Generated columns for watts_int, category, voltage_type
- Cache embeddings to avoid regeneration
- All operations must be async
- Comprehensive error handling with logging

START WITH: Generate docker-compose.yml and db/schema.sql first.

Ask clarifying questions if anything is unclear.
```

---

**END OF COMMAND PACKET**
