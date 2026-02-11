# Problems, Solutions & Design Decisions

A comprehensive log of all challenges faced during development and the design decisions made to solve them.

---

## Phase 1: ETL Pipeline

### Problem 1.1: Embedding Dimension Mismatch
**Issue:** Database expected 384-dimensional vectors, but `bge-m3` model produces 1024-dimensional embeddings.

**Symptoms:**
```
asyncpg.exceptions.DatataMismatchError: expected 384 dimensions, got 1024
```

**Root Cause:** 
- `config.py` had hardcoded `EMBEDDING_DIMENSION = 384`
- Database schema created with `vector(384)`
- `bge-m3` model actually outputs 1024-dim vectors

**Solution:**
1. Updated `config.py`: `EMBEDDING_DIMENSION = 1024`
2. Updated `embeddings.py` default dimension
3. Recreated database schema with `vector(1024)`
4. Re-ran ETL pipeline

**Design Choice:** Always verify model specifications before schema design. Use configuration-driven dimensions.

---

### Problem 1.2: Generated Columns Failed on Upsert
**Issue:** PostgreSQL generated columns (`category`, `series`, `voltage_type`) cannot be explicitly set in INSERT/UPDATE.

**Symptoms:**
```sql
ERROR: cannot insert into column "category"
DETAIL: Column "category" is a generated column
```

**Root Cause:**
- Initial schema used `GENERATED ALWAYS AS` for these columns
- ETL tried to explicitly populate them during upsert
- PostgreSQL forbids writing to generated columns

**Solution:**
1. Migrated from `GENERATED` columns to regular `TEXT` columns
2. Updated `normalizer.py` to compute values during ETL
3. Updated `loader.py` to include columns in INSERT/UPDATE statements
4. Re-ran ETL to populate data

**Design Choice:** 
- **Tradeoff:** Generated columns ensure consistency but reduce flexibility
- **Decision:** Use regular columns + ETL-time computation for better control
- **Benefit:** Can backfill/correct data without schema changes

---

### Problem 1.3: Category/Series Detection Not Working
**Issue:** Semantic search returned empty results because `category` and `series` were NULL.

**Symptoms:**
```
Query: "Find speakers for conference rooms"
Results: [] (empty)
```

**Root Cause:**
1. Generated columns were NULL after migration
2. ETL normalizer extracted category/series but didn't save to DB
3. `retrieval.py` filtered by category, found no matches

**Solution:**
1. Updated `NormalizedProduct.to_db_record()` to include category/series
2. Updated `loader._upsert_product()` SQL to insert these columns
3. Re-ran ETL pipeline
4. Verified with SQL: `SELECT category, COUNT(*) FROM products GROUP BY category;`

**Design Choice:** Always validate data population after schema changes.

---

### Problem 1.4: ETL Timeout on Windows
**Issue:** First ETL run took extremely long (>30 minutes) due to cold start.

**Root Cause:**
- Ollama model not preloaded
- First embedding call downloads model (~2GB)
- 86 products × embedding time without caching

**Solution:**
1. Pre-pull models: `ollama pull bge-m3`
2. Implement caching in `EmbeddingClient`
3. Use batch embedding with concurrency limits

**Design Choice:** Always pre-warm infrastructure before production runs.

---

## Phase 2: RAG Query Engine

### Problem 2.1: Windows Console Encoding Error
**Issue:** Unicode characters in output caused crashes on Windows console.

**Symptoms:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 0
```

**Root Cause:**
- Windows console uses CP1252, not UTF-8
- Test script used Unicode symbols (✅, ❌)

**Solution:**
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
```

**Design Choice:** Always handle encoding explicitly for cross-platform compatibility.

---

### Problem 2.2: LLM Generation Timeout
**Issue:** LLM queries took 30-60 seconds, sometimes timing out.

**Root Cause:**
- `llama3.2:3b` model is slow on CPU
- Default HTTP timeout too short (30s)

**Solution:**
1. Increased timeout to 60s in `httpx.Timeout(60.0)`
2. Documented expected latency in README
3. Considered using smaller model or GPU acceleration

**Design Choice:** 
- **Tradeoff:** Speed vs. accuracy
- **Decision:** Accept slower responses for better quality
- **Future:** Recommend GPU or quantized models for production

---

### Problem 2.3: Semantic Search Empty Results
**Issue:** Even valid queries returned no products.

**Root Cause:**
- NULL category/series from Phase 1 Problem 1.3
- Hybrid search filters required exact matches
- Vector similarity too strict (threshold 0.7)

**Solution:**
1. Fixed category/series population (see 1.3)
2. Lowered similarity threshold to 0.5
3. Made filters optional (OR logic instead of AND)

**Design Choice:** Start with loose filters, tighten based on user feedback.

---

## Phase 3: MCP Server

### Problem 3.1: FastMCP Initialization Error
**Issue:** `FastMCP()` rejected `description` argument.

**Symptoms:**
```python
TypeError: FastMCP.__init__() got an unexpected keyword argument 'description'
```

**Root Cause:**
- Documentation/example used outdated API
- FastMCP 2.x doesn't support `description` in `__init__`

**Solution:**
Removed `description` argument:
```python
mcp = FastMCP(name="bose-product-engine")  # No description
```

**Design Choice:** Always verify API compatibility with installed version.

---

### Problem 3.2: AttributeError - No `app` Attribute
**Issue:** `uvicorn.run(mcp.app)` failed.

**Symptoms:**
```python
AttributeError: 'FastMCP' object has no attribute 'app'
```

**Root Cause:**
- FastMCP 2.x uses internal server management
- Direct access to underlying ASGI app is not exposed

**Solution:**
Use FastMCP's built-in runner:
```python
await mcp.run_http_async(host=host, port=port)
```

**Design Choice:** Use framework-provided methods instead of accessing internals.

---

### Problem 3.3: Browser Error "Client must accept text/event-stream"
**Issue:** Visiting `http://localhost:8000` in browser showed error.

**Symptoms:**
```
406 Not Acceptable
Client must accept text/event-stream
```

**Root Cause:**
- MCP server uses SSE (Server-Sent Events) transport
- Browsers send `Accept: text/html`, not `text/event-stream`
- This is **expected behavior**, not a bug

**Solution:**
1. Document that browser access is not supported
2. Use MCP-compatible client (Claude Desktop, Zed, custom client)
3. Created `test_mcp_client.py` for verification

**Design Choice:** MCP is a protocol, not a web UI. Don't expect browser compatibility.

---

### Problem 3.4: MCP Transport Confusion
**Issue:** `test_mcp_client.py` failed with "unhandled errors in a TaskGroup".

**Root Cause:**
- FastMCP defaults to `streamable-http` transport
- `mcp` library client expected SSE transport
- Mismatch in transport protocol

**Solution:**
```python
await mcp.run_http_async(host=host, port=port, transport='sse')
```

**Design Choice:** Explicitly specify transport instead of relying on defaults.

---

### Problem 3.5: Port Conflicts (8000, 8001, 8002)
**Issue:** "Address already in use" errors when starting server.

**Root Cause:**
- Previous test runs left processes zombie
- Multiple terminal windows with active servers
- Windows doesn't always clean up on Ctrl+C

**Solution:**
1. `netstat -ano | findstr :8000` to find PID
2. `taskkill /F /PID <PID>` to kill
3. Use different port: `--port 8001`
4. Added port check in `debug.ps1`

**Design Choice:** Always verify port availability before binding.

---

## Phase 4: Liability Prevention

### Problem 4.1: No Purchase Intent Detection
**Issue:** System answered commercial queries like "How much is DM3C?"

**Risk:** Legal liability for providing pricing/availability information.

**Solution:**
Implemented "Three-Layer Defense":
1. **Router**: Regex patterns for purchase intent (`price`, `buy`, `stock`)
2. **Engine**: Hardcoded legal response
3. **Generator**: LLM system prompt prohibition

**Design Choice:**
- **Why 3 layers?** Defense in depth - if one fails, others catch it
- **Why Router first?** Cheapest (no LLM call), fastest response
- **Why hardcoded responses?** Legal compliance requires exact wording

---

### Problem 4.2: Competitor Mention Handling
**Issue:** Users asked "How does Bose compare to Sonos?"

**Risk:** Legal/brand risk discussing competitors.

**Solution:**
Added `DOMAIN_VIOLATION` detection:
- Regex for competitor brands (`sonos`, `jbl`, `yamaha`, etc.)
- Return: "I can only provide information on Bose Professional products."

**Design Choice:** Strict domain locking preferred over nuanced handling.

---

## System Design Principles (Learned)

### 1. **Fail Fast, Fail Cheap**
- Router checks (regex) before expensive LLM calls
- Database validation before ETL processing

### 2. **Configuration Over Hardcoding**
- `.env` for all environment-specific values
- `config.py` as single source of truth
- Example: Embedding dimension disaster came from hardcoding

### 3. **Explicit Over Implicit**
- Always specify transport protocol
- Always specify encoding
- Don't rely on framework defaults

### 4. **Defense in Depth**
- Three layers for liability prevention
- Strict fallback + prompt + validation
- Never trust a single control

### 5. **Verify After Change**
- Schema change? Check data population
- Code change? Run regression tests
- ETL change? Query database directly

### 6. **Document Expected Behavior**
- "Browser won't work" is not a bug if documented
- "LLM takes 60s" is fine if users know

### 7. **Infrastructure Before Code**
- Pre-pull models
- Pre-warm databases
- Check ports before binding

---

## Common Pitfalls to Avoid

1. ❌ **Assuming generated columns work everywhere** → Use regular columns + ETL logic
2. ❌ **Ignoring model specifications** → Verify embedding dimensions first
3. ❌ **Not handling encoding** → Explicitly set UTF-8 on Windows
4. ❌ **Trusting framework defaults** → Specify transport, timeouts, etc.
5. ❌ **Skipping port checks** → Always verify availability
6. ❌ **One layer of defense** → Legal compliance needs redundancy
7. ❌ **Testing only happy paths** → Test edge cases (empty results, timeouts)

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Direct Lookup | <100ms | SQL + formatting only |
| Semantic Search | 500ms-2s | Embedding + vector search |
| LLM Generation | 30-60s | CPU-bound, consider GPU |
| Calculation | <50ms | Pure Python math |
| Purchase Intent Block | <10ms | Regex only |

---

## Key Metrics

- **Products in DB**: 86
- **Embedding Dimension**: 1024
- **Average ETL Time**: 5-10 minutes (cold start)
- **Test Coverage**: 4 query types + 2 defense layers
- **Response Accuracy**: Grounded (no hallucinations due to strict prompting)

---

## Future Improvements

1. **Performance**: GPU acceleration for Ollama
2. **Scalability**: Connection pooling, caching layer
3. **Observability**: Structured logging, metrics
4. **Testing**: Golden set for regression testing
5. **Deployment**: Docker containerization, K8s manifests

---

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [PostgreSQL pgvector](https://github.com/pgvector/pgvector)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [MCP Protocol Spec](https://spec.modelcontextprotocol.io/)
