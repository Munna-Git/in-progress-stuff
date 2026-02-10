"""
PDF Extractor using docling library.
Handles table extraction with header propagation for merged cells.
"""

import json
import logging
import hashlib
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
    category_hint: str = ""  # Page title context
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExtractionResult:
    """Result of PDF extraction."""
    pdf_source: str
    tables: list[ExtractedTable]
    total_pages: int
    pdf_hash: str = ""  # For cache validation
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "pdf_source": self.pdf_source,
            "pdf_hash": self.pdf_hash,
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
    - JSON caching with file hash validation
    - Robust table cell extraction
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the PDF extractor."""
        self.cache_dir = cache_dir or settings.processed_path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_hash(self, pdf_path: Path) -> str:
        """Get MD5 hash of PDF file for cache validation."""
        hash_md5 = hashlib.md5()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    async def extract(
        self, 
        pdf_path: Path, 
        force_refresh: bool = False,
    ) -> ExtractionResult:
        """
        Extract all tables from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            force_refresh: If True, skip cache and re-extract
            
        Returns:
            ExtractionResult containing all extracted tables
        """
        logger.info(f"Extracting tables from: {pdf_path}")
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Calculate file hash for cache validation
        file_hash = self._get_file_hash(pdf_path)
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self._load_from_cache(pdf_path, file_hash)
            if cached:
                if cached.tables:
                    logger.info(f"Loaded from cache: {len(cached.tables)} tables")
                    return cached
                else:
                    logger.warning("Cache has 0 tables - re-extracting")
        
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
            logger.info(f"Running docling conversion on {pdf_path.name}...")
            result = converter.convert(str(pdf_path))
            
            # Get total pages
            total_pages = self._get_total_pages(result)
            logger.info(f"PDF has {total_pages} pages")
            
            # Extract tables from document
            tables = []
            errors = []
            
            document_tables = list(result.document.tables)
            logger.info(f"Found {len(document_tables)} tables in document")
            
            # Also try to extract page context for category hints
            page_contexts = self._extract_page_contexts(result)
            
            for table_idx, table in enumerate(document_tables):
                try:
                    # Extract page number from provenance
                    page_number = self._get_table_page(table)
                    
                    # Get category hint from page context
                    category_hint = page_contexts.get(page_number, "")
                    
                    logger.debug(f"Processing table {table_idx} from page {page_number}")
                    
                    extracted = self._process_table(
                        table=table,
                        page_number=page_number,
                        table_index=table_idx,
                        category_hint=category_hint,
                    )
                    
                    if extracted:
                        tables.append(extracted)
                        logger.info(
                            f"Table {table_idx}: page {page_number}, "
                            f"{len(extracted.headers)} columns, {len(extracted.rows)} rows"
                        )
                    else:
                        logger.debug(f"Table {table_idx} skipped (empty or header-only)")
                        
                except Exception as e:
                    error_msg = f"Error processing table {table_idx}: {e}"
                    logger.warning(error_msg, exc_info=True)
                    errors.append(error_msg)
            
            extraction_result = ExtractionResult(
                pdf_source=str(pdf_path.name),
                pdf_hash=file_hash,
                tables=tables,
                total_pages=total_pages,
                errors=errors,
            )
            
            # Only cache if we got tables
            if tables:
                self._save_to_cache(pdf_path, extraction_result)
            else:
                logger.warning("No tables extracted - not caching empty result")
            
            logger.info(f"Extracted {len(tables)} tables from {pdf_path.name}")
            return extraction_result
            
        except ImportError:
            logger.error("docling not installed. Please install with: pip install docling")
            raise
        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}", exc_info=True)
            raise
    
    def _get_total_pages(self, result) -> int:
        """Get total pages from docling result."""
        try:
            if hasattr(result.document, 'num_pages'):
                num_pages = result.document.num_pages
                return num_pages() if callable(num_pages) else num_pages
            # Fallback: count pages from table provenance
            pages = set()
            for table in result.document.tables:
                page = self._get_table_page(table)
                if page:
                    pages.add(page)
            return max(pages) if pages else 0
        except Exception:
            return 0
    
    def _get_table_page(self, table) -> int:
        """Extract page number from table provenance."""
        try:
            if hasattr(table, 'prov') and table.prov:
                prov_item = table.prov[0]
                return getattr(prov_item, 'page_no', 1) or 1
        except Exception:
            pass
        return 1
    
    def _extract_page_contexts(self, result) -> dict[int, str]:
        """Extract page titles/headers for category detection."""
        contexts = {}
        try:
            # Look for text elements that appear to be titles
            if hasattr(result.document, 'texts'):
                for text_elem in result.document.texts:
                    text = getattr(text_elem, 'text', '') or ''
                    if any(kw in text.lower() for kw in [
                        'loudspeaker', 'amplifier', 'controller', 
                        'speaker', 'subwoofer', 'system'
                    ]):
                        page = 1
                        if hasattr(text_elem, 'prov') and text_elem.prov:
                            page = getattr(text_elem.prov[0], 'page_no', 1) or 1
                        contexts[page] = text
        except Exception as e:
            logger.debug(f"Could not extract page contexts: {e}")
        return contexts
    
    def _process_table(
        self,
        table: Any,
        page_number: int,
        table_index: int,
        category_hint: str = "",
    ) -> Optional[ExtractedTable]:
        """
        Process a single table with header propagation.
        
        Handles merged header cells by forward-filling values
        and creating hierarchical column names.
        """
        try:
            # Get table data as grid - try multiple methods
            raw_data = self._extract_table_data(table)
            
            if not raw_data:
                logger.debug(f"Table {table_index}: no raw data extracted")
                return None
            
            if len(raw_data) < 2:
                logger.debug(f"Table {table_index}: only {len(raw_data)} rows (need at least 2)")
                return None
            
            # Apply header propagation for merged cells
            num_header_rows = self._get_header_row_count(raw_data, category_hint)
            headers = self._propagate_headers(raw_data, num_header_rows)
            
            if not headers or all(h == "" for h in headers):
                logger.debug(f"Table {table_index}: no valid headers")
                return None
            
            # Convert data rows to dictionaries
            rows = []
            for row_idx, row_data in enumerate(raw_data[num_header_rows:]):
                row_dict = {}
                for col_idx, value in enumerate(row_data):
                    if col_idx < len(headers):
                        header = headers[col_idx]
                        if not header:
                            header = f"col_{col_idx}"
                        # Clean the value
                        cleaned = self._clean_cell_value(value)
                        if cleaned:
                            row_dict[header] = cleaned
                
                # Only add rows with actual data
                if row_dict and len(row_dict) >= 2:
                    rows.append(row_dict)
            
            if not rows:
                logger.debug(f"Table {table_index}: no valid data rows")
                return None
            
            return ExtractedTable(
                page_number=page_number,
                table_index=table_index,
                headers=headers,
                rows=rows,
                raw_data=[[str(cell) if cell else "" for cell in row] for row in raw_data],
                category_hint=category_hint,
            )
            
        except Exception as e:
            logger.error(f"Error processing table {table_index}: {e}", exc_info=True)
            return None
    
    def _extract_table_data(self, table: Any) -> list[list[str]]:
        """
        Extract table data as a 2D grid from various docling table formats.
        Tries multiple methods to ensure robust extraction.
        """
        raw_data = []
        
        # Method 1: Try export_to_dataframe
        try:
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                if df is not None and not df.empty:
                    # Include column headers as first row
                    headers = [str(c) for c in df.columns.tolist()]
                    raw_data.append(headers)
                    for _, row in df.iterrows():
                        raw_data.append([str(v) if v is not None else "" for v in row.tolist()])
                    if len(raw_data) > 1:
                        logger.debug(f"Extracted via export_to_dataframe: {len(raw_data)} rows")
                        return raw_data
        except Exception as e:
            logger.debug(f"export_to_dataframe failed: {e}")
        
        # Method 2: Try data attribute
        raw_data = []
        try:
            if hasattr(table, 'data') and table.data:
                for row in table.data:
                    grid_row = []
                    if hasattr(row, '__iter__'):
                        for cell in row:
                            if hasattr(cell, 'text'):
                                grid_row.append(str(cell.text) if cell.text else "")
                            elif isinstance(cell, str):
                                grid_row.append(cell)
                            else:
                                grid_row.append(str(cell) if cell else "")
                    raw_data.append(grid_row)
                if raw_data:
                    logger.debug(f"Extracted via data attribute: {len(raw_data)} rows")
                    return raw_data
        except Exception as e:
            logger.debug(f"data attribute extraction failed: {e}")
        
        # Method 3: Try body/grid structure
        raw_data = []
        try:
            body = getattr(table, 'body', None) or getattr(table, 'grid', None)
            if body:
                for row in body:
                    grid_row = []
                    if hasattr(row, '__iter__'):
                        for cell in row:
                            text = ""
                            if hasattr(cell, 'text'):
                                text = str(cell.text) if cell.text else ""
                            elif isinstance(cell, str):
                                text = cell
                            else:
                                text = str(cell) if cell else ""
                            grid_row.append(text)
                    raw_data.append(grid_row)
                if raw_data:
                    logger.debug(f"Extracted via body/grid: {len(raw_data)} rows")
                    return raw_data
        except Exception as e:
            logger.debug(f"body/grid extraction failed: {e}")
        
        # Method 4: Try TableData cells iteration
        raw_data = []
        try:
            if hasattr(table, 'cells'):
                cells = table.cells
                if cells:
                    # Build grid from cells with row/col positions
                    max_row = max((getattr(c, 'row', 0) for c in cells), default=0)
                    max_col = max((getattr(c, 'col', 0) for c in cells), default=0)
                    grid = [[""] * (max_col + 1) for _ in range(max_row + 1)]
                    for cell in cells:
                        row = getattr(cell, 'row', 0)
                        col = getattr(cell, 'col', 0)
                        text = getattr(cell, 'text', "") or ""
                        if row <= max_row and col <= max_col:
                            grid[row][col] = text
                    raw_data = grid
                    if raw_data and any(any(c for c in row) for row in raw_data):
                        logger.debug(f"Extracted via cells: {len(raw_data)} rows")
                        return raw_data
        except Exception as e:
            logger.debug(f"cells extraction failed: {e}")
        
        logger.debug("All extraction methods failed")
        return []
    
    def _propagate_headers(
        self, 
        raw_data: list[list[str]], 
        num_header_rows: int,
    ) -> list[str]:
        """
        Propagate headers for merged cells and create hierarchical names.
        
        Example:
            | Driver Components (spans 3 cols) | Acoustics      |
            | LF      | MF      | HF           | Freq Range     |
            
        Becomes:
            ["Driver_Components_LF", "Driver_Components_MF", 
             "Driver_Components_HF", "Acoustics_Freq_Range"]
        """
        if not raw_data or num_header_rows == 0:
            return []
        
        num_cols = max(len(row) for row in raw_data[:num_header_rows])
        if num_cols == 0:
            return []
        
        headers = [""] * num_cols
        
        for row_idx in range(num_header_rows):
            row = raw_data[row_idx] if row_idx < len(raw_data) else []
            
            # Track last non-empty value for forward-fill (merged cells)
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
    
    def _get_header_row_count(self, raw_data: list[list[str]], category_hint: str = "") -> int:
        """
        Determine how many rows are headers.
        
        Heuristics:
        - Headers often have few empty cells
        - Headers don't contain numeric model numbers typically
        - Look for pattern break between header and data rows
        - ArenaMatch tables have 3-level headers
        """
        if len(raw_data) < 2:
            return 1 if raw_data else 0
        
        # Special case: ArenaMatch tables have 3-level nested headers
        if self._is_arenamatch_table(raw_data, category_hint):
            logger.debug("Detected ArenaMatch table - using 3 header rows")
            return 3 if len(raw_data) >= 3 else min(2, len(raw_data))
        
        # Special case: ShowMatch SM tables have 2-level headers
        if self._is_showmatch_table(raw_data, category_hint):
            logger.debug("Detected ShowMatch table - using 2 header rows")
            return 2 if len(raw_data) >= 2 else 1
        
        first_row = raw_data[0]
        
        # Check if first row looks like headers (mostly text, few numbers)
        first_row_has_numbers = any(
            any(char.isdigit() for char in str(c)) 
            for c in first_row if c
        )
        
        if len(raw_data) < 2:
            return 1
        
        second_row = raw_data[1]
        
        # Check if second row looks like sub-headers
        second_row_is_header = False
        if second_row:
            non_empty = [c for c in second_row if c and str(c).strip()]
            if non_empty:
                # Sub-headers often have unit indicators or short text
                has_units = any(
                    any(unit in str(c).lower() for unit in ['hz', 'khz', 'w', 'ohm', 'db', 'mm', 'kg', 'lb'])
                    for c in non_empty
                )
                has_model_pattern = any(
                    self._looks_like_model_name(str(c)) for c in non_empty
                )
                # If second row has units but no model patterns, it's likely a sub-header
                if has_units and not has_model_pattern:
                    second_row_is_header = True
                # Or if mostly empty
                empty_ratio = 1 - (len(non_empty) / len(second_row))
                if empty_ratio > 0.5:
                    second_row_is_header = True
                
                # Check for 3rd level headers (model variants like AM10/60, AM10/80)
                if len(raw_data) >= 3 and second_row_is_header:
                    third_row = raw_data[2]
                    third_non_empty = [c for c in third_row if c and str(c).strip()]
                    if third_non_empty:
                        # Check if third row has model variant patterns
                        has_variant_pattern = any(
                            self._looks_like_model_variant(str(c)) for c in third_non_empty
                        )
                        if has_variant_pattern:
                            logger.debug("Detected 3-level headers with model variants")
                            return 3
        
        return 2 if second_row_is_header else 1
    
    def _is_arenamatch_table(self, raw_data: list[list[str]], category_hint: str = "") -> bool:
        """Detect if this is an ArenaMatch table with 3-level headers."""
        # Check category hint
        if 'arenamatch' in category_hint.lower() or 'arrayable' in category_hint.lower():
            return True
        
        # Check first row for ArenaMatch pattern
        if raw_data:
            first_row_text = ' '.join(str(c).lower() for c in raw_data[0] if c)
            if 'arenamatch' in first_row_text or 'am (arena' in first_row_text:
                return True
        
        # Check for AM10/AM20/AM40 pattern in first 3 rows
        import re
        for row in raw_data[:3]:
            row_text = ' '.join(str(c) for c in row if c)
            if re.search(r'AM\s*\d{2}(?:/\d{2,3})?', row_text, re.IGNORECASE):
                if any(f'AM{n}' in row_text for n in ['10', '20', '40']):
                    return True
        
        return False
    
    def _is_showmatch_table(self, raw_data: list[list[str]], category_hint: str = "") -> bool:
        """Detect if this is a ShowMatch table with 2-level headers."""
        if 'showmatch' in category_hint.lower():
            return True
        
        if raw_data:
            first_row_text = ' '.join(str(c).lower() for c in raw_data[0] if c)
            if 'showmatch' in first_row_text or 'sm (showmatch)' in first_row_text:
                return True
            
            # Check for SM5/SM10/SM20 pattern
            import re
            for row in raw_data[:2]:
                row_text = ' '.join(str(c) for c in row if c)
                if re.search(r'SM\s*\d+', row_text, re.IGNORECASE):
                    return True
        
        return False
    
    def _looks_like_model_variant(self, value: str) -> bool:
        """Check if value looks like a model variant (e.g., AM10/60, AM10/80)."""
        import re
        patterns = [
            r'^AM\d+/\d+',           # AM10/60, AM20/80
            r'^\d+°?\s*[×x]\s*\d+',  # Coverage angles like 60° x 10°
            r'^\d+/\d+/\d+',         # Triple variants
        ]
        for pattern in patterns:
            if re.match(pattern, value.strip(), re.IGNORECASE):
                return True
        return False
    
    def _looks_like_model_name(self, value: str) -> bool:
        """Check if a value looks like a Bose model name."""
        import re
        patterns = [
            r'^[A-Z]{2,4}\d+',      # AM10, DM3SE, FS2SE
            r'^[A-Z]+\s*\d+-',      # IZA 250-LZ
            r'^P\d{4}[A-Z]?',       # P4300A
            r'^CC-\d',              # CC-1, CC-2D
        ]
        for pattern in patterns:
            if re.match(pattern, value.strip(), re.IGNORECASE):
                return True
        return False
    
    def _clean_header_value(self, value: Any) -> str:
        """Clean and normalize header value."""
        import re
        
        if value is None:
            return ""
        
        text = str(value).strip()
        
        # Remove special characters, keep alphanumeric and spaces
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
        if not text or text in ('—', '-', '–', 'N/A', 'n/a', '', 'nan', 'None'):
            return None
        
        return text
    
    def _get_cache_path(self, pdf_path: Path) -> Path:
        """Get cache file path for a PDF."""
        return self.cache_dir / f"{pdf_path.stem}_extracted.json"
    
    def _load_from_cache(
        self, 
        pdf_path: Path, 
        current_hash: str,
    ) -> Optional[ExtractionResult]:
        """Load extraction result from cache if valid."""
        cache_path = self._get_cache_path(pdf_path)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate hash
            cached_hash = data.get('pdf_hash', '')
            if cached_hash and cached_hash != current_hash:
                logger.info("Cache hash mismatch - PDF modified, re-extracting")
                return None
            
            # Check for empty tables
            if not data.get('tables'):
                logger.info("Cache has no tables - re-extracting")
                return None
            
            tables = [
                ExtractedTable(**t) for t in data.get('tables', [])
            ]
            
            return ExtractionResult(
                pdf_source=data['pdf_source'],
                pdf_hash=cached_hash,
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
    
    def clear_cache(self, pdf_path: Optional[Path] = None) -> None:
        """Clear extraction cache."""
        if pdf_path:
            cache_path = self._get_cache_path(pdf_path)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared cache: {cache_path}")
        else:
            for cache_file in self.cache_dir.glob("*_extracted.json"):
                cache_file.unlink()
            logger.info(f"Cleared all cache files in {self.cache_dir}")
    
    async def extract_all(
        self, 
        pdf_dir: Optional[Path] = None,
        force_refresh: bool = False,
    ) -> list[ExtractionResult]:
        """
        Extract tables from all PDFs in a directory.
        
        Args:
            pdf_dir: Directory containing PDF files (defaults to settings.raw_pdfs_path)
            force_refresh: If True, skip cache and re-extract all
            
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
                result = await self.extract(pdf_path, force_refresh=force_refresh)
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
