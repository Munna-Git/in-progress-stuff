"""
ETL Pipeline Orchestrator.
Coordinates extraction, normalization, synthesis, and loading.
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.config import settings
from src.database import get_db
from src.etl.extractor import PDFExtractor, ExtractionResult
from src.etl.normalizer import ProductNormalizer, NormalizationResult
from src.etl.synthesizer import OllamaSynthesizer
from src.etl.loader import ProductLoader

logger = logging.getLogger(__name__)


class ETLPipeline:
    """
    Main ETL pipeline orchestrator.
    
    Pipeline stages:
    1. Extract: Parse PDFs with docling
    2. Normalize: Explode model ranges, parse units
    3. Synthesize: Generate AI summaries (optional)
    4. Load: Insert into PostgreSQL with embeddings
    """
    
    def __init__(
        self,
        pdf_dir: Optional[Path] = None,
        skip_synthesis: bool = False,
        create_vector_index: bool = True,
        force_refresh: bool = False,
    ):
        """
        Initialize the ETL pipeline.
        
        Args:
            pdf_dir: Directory containing PDF files
            skip_synthesis: Skip AI summary generation
            create_vector_index: Create IVFFlat index after loading
            force_refresh: Skip cache and re-extract from PDFs
        """
        self.pdf_dir = pdf_dir or settings.raw_pdfs_path
        self.skip_synthesis = skip_synthesis
        self.create_vector_index = create_vector_index
        self.force_refresh = force_refresh
        
        self.job_id = str(uuid.uuid4())
        self.start_time: Optional[float] = None
        self.stats: dict[str, Any] = {}
    
    async def run(self) -> dict[str, Any]:
        """
        Execute the complete ETL pipeline.
        
        Returns:
            Pipeline statistics and results
        """
        self.start_time = time.time()
        
        logger.info(f"Starting ETL pipeline - Job ID: {self.job_id}")
        logger.info(f"PDF directory: {self.pdf_dir}")
        
        # Initialize stats
        self.stats = {
            "job_id": self.job_id,
            "started_at": datetime.now().isoformat(),
            "pdf_dir": str(self.pdf_dir),
            "stages": {},
            "errors": [],
            "status": "running",
        }
        
        try:
            # Log job start to database
            await self._log_job_start()
            
            # Stage 1: Extract
            extraction_results = await self._run_extraction()
            
            # Stage 2: Normalize
            normalization_result = await self._run_normalization(extraction_results)
            
            # Stage 3: Synthesize (optional)
            products = [p.to_dict() for p in normalization_result.products]
            if not self.skip_synthesis:
                products = await self._run_synthesis(products)
            
            # Stage 4: Load
            load_stats = await self._run_loading(products)
            
            # Create vector index
            if self.create_vector_index:
                await self._create_vector_index()
            
            # Finalize
            elapsed = time.time() - self.start_time
            self.stats["elapsed_seconds"] = round(elapsed, 2)
            self.stats["status"] = "completed"
            self.stats["completed_at"] = datetime.now().isoformat()
            
            logger.info(f"ETL pipeline completed in {elapsed:.2f}s")
            
            # Log job completion
            await self._log_job_complete(load_stats)
            
            return self.stats
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}", exc_info=True)
            self.stats["status"] = "failed"
            self.stats["errors"].append(str(e))
            
            await self._log_job_failed(str(e))
            
            raise
    
    async def _run_extraction(self) -> list[dict]:
        """Run the extraction stage."""
        logger.info("Stage 1: Extraction")
        stage_start = time.time()
        
        extractor = PDFExtractor()
        
        # Clear cache if force refresh
        if self.force_refresh:
            logger.info("Force refresh enabled - clearing extraction cache")
            extractor.clear_cache()
        
        results = await extractor.extract_all(self.pdf_dir, force_refresh=self.force_refresh)
        
        # Save raw tables
        extractor.save_raw_tables(results)
        
        # Convert to dicts for next stage
        extraction_dicts = [r.to_dict() for r in results]
        
        elapsed = time.time() - stage_start
        self.stats["stages"]["extraction"] = {
            "elapsed_seconds": round(elapsed, 2),
            "pdfs_processed": len(results),
            "tables_extracted": sum(len(r.tables) for r in results),
            "errors": sum(len(r.errors) for r in results),
        }
        
        logger.info(
            f"Extraction complete: {len(results)} PDFs, "
            f"{self.stats['stages']['extraction']['tables_extracted']} tables "
            f"in {elapsed:.2f}s"
        )
        
        return extraction_dicts
    
    async def _run_normalization(self, extraction_results: list[dict]) -> NormalizationResult:
        """Run the normalization stage."""
        logger.info("Stage 2: Normalization")
        stage_start = time.time()
        
        normalizer = ProductNormalizer()
        result = await normalizer.normalize(extraction_results)
        
        elapsed = time.time() - stage_start
        self.stats["stages"]["normalization"] = {
            "elapsed_seconds": round(elapsed, 2),
            "products_created": len(result.products),
            "rows_exploded": result.stats.get("rows_exploded", 0),
            "errors": len(result.errors),
        }
        
        logger.info(
            f"Normalization complete: {len(result.products)} products "
            f"({result.stats.get('rows_exploded', 0)} exploded) "
            f"in {elapsed:.2f}s"
        )
        
        return result
    
    async def _run_synthesis(self, products: list[dict]) -> list[dict]:
        """Run the synthesis stage."""
        logger.info("Stage 3: Synthesis")
        stage_start = time.time()
        
        async with OllamaSynthesizer() as synthesizer:
            # Check if Ollama is available
            if not await synthesizer.health_check():
                logger.warning("Ollama not available, skipping synthesis")
                self.stats["stages"]["synthesis"] = {
                    "elapsed_seconds": 0,
                    "skipped": True,
                    "reason": "Ollama not available",
                }
                return products
            
            result = await synthesizer.synthesize_batch(products)
        
        elapsed = time.time() - stage_start
        summaries_generated = sum(1 for p in result if p.get('ai_summary'))
        
        self.stats["stages"]["synthesis"] = {
            "elapsed_seconds": round(elapsed, 2),
            "summaries_generated": summaries_generated,
            "skipped": False,
        }
        
        logger.info(
            f"Synthesis complete: {summaries_generated}/{len(products)} summaries "
            f"in {elapsed:.2f}s"
        )
        
        return result
    
    async def _run_loading(self, products: list[dict]) -> dict:
        """Run the loading stage."""
        logger.info("Stage 4: Loading")
        stage_start = time.time()
        
        async with ProductLoader() as loader:
            load_stats = await loader.load(products)
        
        elapsed = time.time() - stage_start
        self.stats["stages"]["loading"] = {
            "elapsed_seconds": round(elapsed, 2),
            **load_stats,
        }
        
        logger.info(
            f"Loading complete: {load_stats['inserted']} inserted, "
            f"{load_stats['updated']} updated, "
            f"{load_stats['embeddings_generated']} embeddings generated "
            f"in {elapsed:.2f}s"
        )
        
        return load_stats
    
    async def _create_vector_index(self) -> None:
        """Create vector similarity index."""
        logger.info("Creating vector index...")
        
        async with ProductLoader() as loader:
            success = await loader.create_vector_index()
        
        self.stats["vector_index_created"] = success
    
    async def _log_job_start(self) -> None:
        """Log job start to database."""
        try:
            db = await get_db()
            await db.execute(
                """
                INSERT INTO etl_jobs (job_id, status, pdf_source)
                VALUES ($1, 'running', $2)
                """,
                uuid.UUID(self.job_id),
                str(self.pdf_dir),
            )
        except Exception as e:
            logger.warning(f"Failed to log job start: {e}")
    
    async def _log_job_complete(self, load_stats: dict) -> None:
        """Log job completion to database."""
        try:
            db = await get_db()
            await db.execute(
                """
                UPDATE etl_jobs SET
                    status = 'completed',
                    products_extracted = $2,
                    products_loaded = $3,
                    completed_at = NOW()
                WHERE job_id = $1
                """,
                uuid.UUID(self.job_id),
                self.stats["stages"]["normalization"]["products_created"],
                load_stats.get("inserted", 0) + load_stats.get("updated", 0),
            )
        except Exception as e:
            logger.warning(f"Failed to log job completion: {e}")
    
    async def _log_job_failed(self, error: str) -> None:
        """Log job failure to database."""
        try:
            db = await get_db()
            await db.execute(
                """
                UPDATE etl_jobs SET
                    status = 'failed',
                    errors = $2,
                    completed_at = NOW()
                WHERE job_id = $1
                """,
                uuid.UUID(self.job_id),
                json.dumps([error]),
            )
        except Exception as e:
            logger.warning(f"Failed to log job failure: {e}")


async def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Bose Product Engine ETL Pipeline"
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=None,
        help="Directory containing PDF files",
    )
    parser.add_argument(
        "--skip-synthesis",
        action="store_true",
        help="Skip AI summary generation",
    )
    parser.add_argument(
        "--no-vector-index",
        action="store_true",
        help="Skip vector index creation",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Skip cache and re-extract all PDFs",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cache files and exit",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=settings.log_format,
    )
    
    # Ensure directories exist
    settings.ensure_directories()
    
    # Handle cache clearing
    if args.clear_cache:
        from src.etl.extractor import PDFExtractor
        extractor = PDFExtractor()
        extractor.clear_cache()
        print("Cache cleared successfully")
        return 0
    
    # Run pipeline
    pipeline = ETLPipeline(
        pdf_dir=args.pdf_dir,
        skip_synthesis=args.skip_synthesis,
        create_vector_index=not args.no_vector_index,
        force_refresh=args.force_refresh,
    )
    
    try:
        stats = await pipeline.run()
        
        # Print summary
        print("\n" + "="*50)
        print("ETL Pipeline Summary")
        print("="*50)
        print(f"Status: {stats['status']}")
        print(f"Duration: {stats.get('elapsed_seconds', 0):.2f}s")
        print(f"Products created: {stats['stages']['normalization']['products_created']}")
        print(f"Products loaded: {stats['stages']['loading']['inserted'] + stats['stages']['loading']['updated']}")
        print("="*50)
        
        return 0
        
    except Exception as e:
        print(f"\nETL Pipeline failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
