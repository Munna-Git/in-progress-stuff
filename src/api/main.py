
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
from pydantic import BaseModel
from typing import List, Optional, Any

from src.rag.engine import get_engine, QueryEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Bose Product Engine API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine instance
engine: Optional[QueryEngine] = None

class QueryRequest(BaseModel):
    query: str

class Citation(BaseModel):
    model_name: str
    field: str
    value: Any
    pdf_source: Optional[str]

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    confidence: float
    query_type: str
    products_used: List[str]

@app.on_event("startup")
async def startup_event():
    global engine
    engine = await get_engine()
    logger.info("RAG Engine initialized")

@app.on_event("shutdown")
async def shutdown_event():
    global engine
    if engine:
        await engine.close()
        logger.info("RAG Engine closed")

@app.get("/health")
async def health():
    return {"status": "ok", "engine_ready": engine is not None}

@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    
    try:
        result = await engine.query(request.query)
        
        # Convert result to response model
        citations = [
            Citation(
                model_name=c.model_name,
                field=c.field,
                value=c.value,
                pdf_source=c.pdf_source
            ) for c in result.citations
        ]
        
        return QueryResponse(
            answer=result.answer,
            citations=citations,
            confidence=result.confidence,
            query_type=result.query_type,
            products_used=result.products_used
        )
            
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Mount static UI files last (catch-all)
app.mount("/", StaticFiles(directory="src/ui", html=True), name="ui")
