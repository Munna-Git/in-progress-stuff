"""
PDF Extractor using docling library.
Handles table extraction with header propagation for merged cells.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Represents an extracted table from a PDF page."""
    page_number: int
    table_index: int
    headers: list[str]
    rows: list[dict[str, Any]]
    raw_data: list[list[str]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExtractionResult:
    """Result of PDF extraction."""
    pdf_source: str
    tables: list[ExtractedTable]
    total_pages: int
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "pdf_source": self.pdf_source,
            "tables": [t.to_dict() for t in self.tables],
            "total_pages": self.total_pages,
            "errors": self.errors,
        }


class PDFExtractor:
    """
    Extracts tables from Bose product PDFs using docling.
    
    Key Features:
    - Header propagation for merged cells
    - Hierarchical column naming (e.g., Driver_Components_LF)
    - JSON caching for processed results
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the PDF extractor."""
        self.cache_dir = cache_dir or settings.processed_path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def extract(self, pdf_path: Path) -> ExtractionResult:
        """
        Extract all tables from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            ExtractionResult containing all extracted tables
        """
        logger.info(f"Extracting tables from: {pdf_path}")
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Check cache first
        cached = self._load_from_cache(pdf_path)
        if cached:
            logger.info(f"Loaded from cache: {len(cached.tables)} tables")
            return cached
        
        try:
            # Import docling (delay import for optional dependency)
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption
            
            # Configure docling for table extraction
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_table_structure = True
            pipeline_options.do_ocr = False  # Tables are usually text-based
            
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            
            # Convert PDF
            result = converter.convert(str(pdf_path))
            
            # Extract tables from document
            tables = []
            errors = []
            
            for table_idx, table in enumerate(result.document.tables):
                try:
                    extracted = self._process_table(
                        table=table,
                        page_number=getattr(table, 'prov', [{}])[0].get('page_no', 1) if hasattr(table, 'prov') else 1,
                        table_index=table_idx,
                    )
                    if extracted:
                        tables.append(extracted)
                except Exception as e:
                    error_msg = f"Error processing table {table_idx}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            extraction_result = ExtractionResult(
                pdf_source=str(pdf_path.name),
                tables=tables,
                total_pages=result.document.num_pages if hasattr(result.document, 'num_pages') else len(set(t.page_number for t in tables)),
                errors=errors,
            )
            
            # Cache the result
            self._save_to_cache(pdf_path, extraction_result)
            
            logger.info(f"Extracted {len(tables)} tables from {pdf_path.name}")
            return extraction_result
            
        except ImportError:
            logger.error("docling not installed. Please install with: pip install docling")
            raise
        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}")
            raise
    
    def _process_table(
        self,
        table: Any,
        page_number: int,
        table_index: int,
    ) -> Optional[ExtractedTable]:
        """
        Process a single table with header propagation.
        
        Handles merged header cells by forward-filling values
        and creating hierarchical column names.
        """
        try:
            # Get table data as grid
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                raw_data = [df.columns.tolist()] + df.values.tolist()
            elif hasattr(table, 'data'):
                raw_data = table.data
            else:
                # Try to extract from table cells
                raw_data = self._extract_table_grid(table)
            
            if not raw_data or len(raw_data) < 2:
                logger.debug(f"Skipping empty or header-only table {table_index}")
                return None
            
            # Apply header propagation for merged cells
            headers = self._propagate_headers(raw_data)
            
            # Convert rows to dictionaries
            rows = []
            for row_data in raw_data[self._get_header_row_count(raw_data):]:
                row_dict = {}
                for idx, value in enumerate(row_data):
                    if idx < len(headers):
                        header = headers[idx]
                        # Clean the value
                        cleaned = self._clean_cell_value(value)
                        if cleaned:
                            row_dict[header] = cleaned
                if row_dict:
                    rows.append(row_dict)
            
            return ExtractedTable(
                page_number=page_number,
                table_index=table_index,
                headers=headers,
                rows=rows,
                raw_data=[[str(cell) for cell in row] for row in raw_data],
            )
            
        except Exception as e:
            logger.error(f"Error processing table: {e}")
            return None
    
    def _extract_table_grid(self, table: Any) -> list[list[str]]:
        """Extract table data as a 2D grid from various table formats."""
        grid = []
        
        if hasattr(table, 'body'):
            # docling TableData format
            for row in table.body:
                grid_row = []
                for cell in row:
                    if hasattr(cell, 'text'):
                        grid_row.append(cell.text)
                    else:
                        grid_row.append(str(cell))
                grid.append(grid_row)
        
        return grid
    
    def _propagate_headers(self, raw_data: list[list[str]]) -> list[str]:
        """
        Propagate headers for merged cells and create hierarchical names.
        
        Example:
            | Driver Components (spans 3 cols) | Acoustics      |
            | LF      | MF      | HF           | Freq Range     |
            
        Becomes:
            ["Driver_Components_LF", "Driver_Components_MF", 
             "Driver_Components_HF", "Acoustics_Freq_Range"]
        """
        if not raw_data:
            return []
        
        # Determine number of header rows (rows with mostly empty or merged cells)
        num_header_rows = self._get_header_row_count(raw_data)
        
        if num_header_rows == 0:
            # No clear headers, use column indices
            return [f"col_{i}" for i in range(len(raw_data[0]))]
        
        # Build hierarchical headers
        num_cols = max(len(row) for row in raw_data[:num_header_rows])
        headers = [""] * num_cols
        
        for row_idx in range(num_header_rows):
            row = raw_data[row_idx] if row_idx < len(raw_data) else []
            
            # Track last non-empty value for forward-fill
            last_value = ""
            
            for col_idx in range(num_cols):
                cell_value = row[col_idx] if col_idx < len(row) else ""
                cell_value = self._clean_header_value(cell_value)
                
                # Forward-fill empty cells (merged cell propagation)
                if not cell_value and last_value:
                    cell_value = last_value
                elif cell_value:
                    last_value = cell_value
                
                # Append to hierarchical header
                if cell_value:
                    if headers[col_idx]:
                        headers[col_idx] += "_" + cell_value
                    else:
                        headers[col_idx] = cell_value
        
        # Ensure unique headers
        seen = {}
        unique_headers = []
        for h in headers:
            if not h:
                h = "unknown"
            base = h
            count = seen.get(base, 0)
            if count > 0:
                h = f"{base}_{count}"
            seen[base] = count + 1
            unique_headers.append(h)
        
        return unique_headers
    
    def _get_header_row_count(self, raw_data: list[list[str]]) -> int:
        """
        Determine how many rows are headers.
        
        Heuristics:
        - Headers often have many empty cells (merged)
        - Headers don't contain numbers typically
        - Look for pattern break (data rows have more diverse content)
        """
        if len(raw_data) < 2:
            return 1 if raw_data else 0
        
        # Simple heuristic: first 1-2 rows are headers
        # Check if second row looks like sub-headers
        first_row = raw_data[0]
        second_row = raw_data[1] if len(raw_data) > 1 else []
        
        # If second row has many empty cells or no numbers, it's likely a sub-header
        second_row_is_header = False
        if second_row:
            non_empty = [c for c in second_row if c and str(c).strip()]
            has_numbers = any(any(char.isdigit() for char in str(c)) for c in non_empty)
            empty_ratio = 1 - (len(non_empty) / len(second_row)) if second_row else 0
            
            # Sub-header if mostly text with few numbers and some empty cells
            if not has_numbers or empty_ratio > 0.3:
                second_row_is_header = True
        
        return 2 if second_row_is_header else 1
    
    def _clean_header_value(self, value: Any) -> str:
        """Clean and normalize header value."""
        if value is None:
            return ""
        
        text = str(value).strip()
        
        # Remove special characters, keep alphanumeric and spaces
        import re
        text = re.sub(r'[^\w\s-]', '', text)
        
        # Replace spaces and hyphens with underscores
        text = re.sub(r'[\s-]+', '_', text)
        
        # Remove leading/trailing underscores
        text = text.strip('_')
        
        return text
    
    def _clean_cell_value(self, value: Any) -> Optional[str]:
        """Clean cell value for storage."""
        if value is None:
            return None
        
        text = str(value).strip()
        
        # Return None for empty or placeholder values
        if not text or text in ('—', '-', '–', 'N/A', 'n/a', ''):
            return None
        
        return text
    
    def _get_cache_path(self, pdf_path: Path) -> Path:
        """Get cache file path for a PDF."""
        return self.cache_dir / f"{pdf_path.stem}_extracted.json"
    
    def _load_from_cache(self, pdf_path: Path) -> Optional[ExtractionResult]:
        """Load extraction result from cache if valid."""
        cache_path = self._get_cache_path(pdf_path)
        
        if not cache_path.exists():
            return None
        
        # Check if cache is stale (PDF modified after cache)
        if pdf_path.stat().st_mtime > cache_path.stat().st_mtime:
            logger.info("Cache is stale, re-extracting")
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            tables = [
                ExtractedTable(**t) for t in data.get('tables', [])
            ]
            
            return ExtractionResult(
                pdf_source=data['pdf_source'],
                tables=tables,
                total_pages=data['total_pages'],
                errors=data.get('errors', []),
            )
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None
    
    def _save_to_cache(self, pdf_path: Path, result: ExtractionResult) -> None:
        """Save extraction result to cache."""
        cache_path = self._get_cache_path(pdf_path)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    async def extract_all(self, pdf_dir: Optional[Path] = None) -> list[ExtractionResult]:
        """
        Extract tables from all PDFs in a directory.
        
        Args:
            pdf_dir: Directory containing PDF files (defaults to settings.raw_pdfs_path)
            
        Returns:
            List of ExtractionResult for each PDF
        """
        pdf_dir = pdf_dir or settings.raw_pdfs_path
        
        if not pdf_dir.exists():
            logger.warning(f"PDF directory not found: {pdf_dir}")
            return []
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in: {pdf_dir}")
            return []
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        results = []
        for pdf_path in pdf_files:
            try:
                result = await self.extract(pdf_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract {pdf_path}: {e}")
                results.append(ExtractionResult(
                    pdf_source=str(pdf_path.name),
                    tables=[],
                    total_pages=0,
                    errors=[str(e)],
                ))
        
        return results
    
    def save_raw_tables(self, results: list[ExtractionResult]) -> Path:
        """
        Save all extraction results to a combined JSON file.
        
        Returns:
            Path to the saved JSON file
        """
        output_path = settings.raw_tables_cache
        
        all_data = [r.to_dict() for r in results]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved raw tables to: {output_path}")
        return output_path
