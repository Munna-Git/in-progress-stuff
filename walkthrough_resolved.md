# Bose Professional Product Engine - Complete Walkthrough

## Summary
Built a complete zero-hallucination product search system for Bose professional audio equipment. All 3 phases implemented with 100% local-first architecture.

---

## Project Structure

```
bose-product-engine/
├── docker-compose.yml          # PostgreSQL 16 + pgvector
├── db/schema.sql               # Schema with generated columns
├── pyproject.toml              # Dependencies
├── README.md                   # Setup instructions
│
├── src/
│   ├── config.py               # Pydantic settings
│   ├── database.py             # asyncpg connection pool
│   │
│   ├── etl/                    # Phase 1: ETL Pipeline
│   │   ├── extractor.py        # docling PDF extraction
│   │   ├── normalizer.py       # Row explosion + unit parsing
│   │   ├── synthesizer.py      # Ollama summaries
│   │   ├── loader.py           # Embeddings + DB insert
│   │   └── pipeline.py         # Orchestrator + CLI
│   │
│   ├── rag/                    # Phase 2: RAG System
│   │   ├── embeddings.py       # Ollama embedding client
│   │   ├── router.py           # Intent classification
│   │   ├── retrieval.py        # Hybrid SQL + vector search
│   │   ├── generator.py        # Answer with citations
│   │   └── engine.py           # Query orchestrator
│   │
│   ├── logic/                  # Electrical Calculations
│   │   └── calculator.py       # 70V/100V math (NO LLM)
│   │
│   └── server/                 # Phase 3: MCP Server
│       ├── tools.py            # Tool definitions
│       └── main.py             # FastMCP server
│
└── tests/
    ├── golden_set.json         # 20 test cases
    └── run_accuracy.py         # Evaluation runner
```

---

## Key Features

### ETL Pipeline
- **Header Propagation**: Handles merged PDF cells
- **Row Explosion**: `AM10/60/80` → `AM10/60`, `AM10/80`
- **Unit Parsing**: `"125 W"` → `power_watts: 125`

### RAG System
- **Intent Classification**: Rules + LLM fallback
- **Hybrid Search**: SQL filters + vector reranking
- **Citations**: Every answer cites source data

### Electrical Calculator
- **Zero LLM**: Pure Python math
- **70V Compatibility**: Load vs transformer capacity
- **Impedance**: Series/parallel calculations

---

## Quick Start

```powershell
# Start database
docker compose up -d

# Install dependencies
pip install -e .

# Pull Ollama models
ollama pull bge-m3
ollama pull llama3.2:3b

# Run ETL
python -m src.etl.pipeline

# Start MCP server
python -m src.server.main

# Run tests
python tests/run_accuracy.py
```

---

## Files Created

| Phase | Files | Purpose |
|-------|-------|---------|
| Phase 1 | 9 files | Database + ETL |
| Phase 2 | 7 files | RAG + Calculator |
| Phase 3 | 5 files | Server + Tests |
| **Total** | **21 files** | ~145KB code |
