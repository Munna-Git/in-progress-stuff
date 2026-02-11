-- Bose Professional Product Engine Schema
-- PostgreSQL 16 + pgvector

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ===========================================
-- PRODUCTS TABLE
-- ===========================================
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    model_name TEXT UNIQUE NOT NULL,
    
    -- Flexible JSONB storage for all specs
    specs JSONB NOT NULL DEFAULT '{}',
    
    -- AI-generated summary for semantic search
    ai_summary TEXT,
    
    -- ===========================================
    -- GENERATED COLUMNS (for fast SQL filtering)
    -- ===========================================
    
    -- Power in watts (extracted from specs.power_watts)
    watts_int INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN specs->>'power_watts' ~ '^\d+$' 
            THEN (specs->>'power_watts')::INTEGER 
            ELSE NULL 
        END
    ) STORED,
    
    -- Product category (speakers, amplifiers, controllers, etc.)
    category TEXT GENERATED ALWAYS AS (
        specs->>'category'
    ) STORED,
    
    -- Voltage type for distributed audio (70V, 100V, Low-Z)
    voltage_type TEXT GENERATED ALWAYS AS (
        specs->>'voltage_type'
    ) STORED,
    
    -- Product series (DesignMax, FreeSpace, ArenaMatch, etc.)
    series TEXT GENERATED ALWAYS AS (
        specs->>'series'
    ) STORED,
    
    -- ===========================================
    -- VECTOR EMBEDDING (1024 dims = Ollama bge-m3)
    -- ===========================================
    embedding vector(1024),
    
    -- ===========================================
    -- METADATA
    -- ===========================================
    pdf_source TEXT,
    page_number INTEGER,
    raw_text TEXT,  -- Original extracted text for debugging
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===========================================
-- INDEXES FOR <3 SECOND QUERY PERFORMANCE
-- ===========================================

-- B-tree indexes for exact filtering
CREATE INDEX IF NOT EXISTS idx_products_watts 
    ON products(watts_int) 
    WHERE watts_int IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_category 
    ON products(category) 
    WHERE category IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_voltage 
    ON products(voltage_type) 
    WHERE voltage_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_series 
    ON products(series) 
    WHERE series IS NOT NULL;

-- GIN index for JSONB containment queries
CREATE INDEX IF NOT EXISTS idx_products_specs_gin 
    ON products USING GIN(specs);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_products_model_trgm 
    ON products USING GIN(model_name gin_trgm_ops);

-- Vector similarity index (IVFFlat for ~100 products)
-- Note: Must have data before creating IVFFlat index
-- We'll create this after data load, or use HNSW for small datasets

-- ===========================================
-- EMBEDDING CACHE TABLE
-- ===========================================
CREATE TABLE IF NOT EXISTS embedding_cache (
    id SERIAL PRIMARY KEY,
    text_hash TEXT UNIQUE NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    model_name TEXT DEFAULT 'bge-m3',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash 
    ON embedding_cache(text_hash);

-- ===========================================
-- ETL JOB LOG TABLE
-- ===========================================
CREATE TABLE IF NOT EXISTS etl_jobs (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed
    pdf_source TEXT,
    products_extracted INTEGER DEFAULT 0,
    products_loaded INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_etl_jobs_status 
    ON etl_jobs(status);

-- ===========================================
-- HELPER FUNCTIONS
-- ===========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for products table
DROP TRIGGER IF EXISTS update_products_updated_at ON products;
CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- VIEWS FOR COMMON QUERIES
-- ===========================================

-- View: Products with embeddings
CREATE OR REPLACE VIEW products_with_embeddings AS
SELECT 
    id,
    model_name,
    category,
    series,
    watts_int,
    voltage_type,
    ai_summary,
    embedding IS NOT NULL as has_embedding
FROM products;

-- View: Category statistics
CREATE OR REPLACE VIEW category_stats AS
SELECT 
    category,
    COUNT(*) as product_count,
    AVG(watts_int) as avg_watts,
    MIN(watts_int) as min_watts,
    MAX(watts_int) as max_watts
FROM products
WHERE category IS NOT NULL
GROUP BY category
ORDER BY product_count DESC;

-- ===========================================
-- POST-LOAD INDEX (run after data insert)
-- ===========================================
-- Run this after loading data:
-- CREATE INDEX IF NOT EXISTS idx_products_embedding_ivfflat 
--     ON products USING ivfflat(embedding vector_cosine_ops) 
--     WITH (lists = 10);
