"""
Product Normalizer for Bose specifications.
Handles row explosion for model ranges and unit parsing.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional, Union

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NormalizedProduct:
    """A normalized product with parsed specifications."""
    model_name: str
    category: str
    series: str
    specs: dict[str, Any]
    pdf_source: str
    page_number: int
    raw_text: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizationResult:
    """Result of normalization process."""
    products: list[NormalizedProduct]
    errors: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "products": [p.to_dict() for p in self.products],
            "errors": self.errors,
            "stats": self.stats,
        }


class ProductNormalizer:
    """
    Normalizes extracted table data into product records.
    
    Key Features:
    - Row explosion for model ranges (AM10/60/80 → AM10/60, AM10/80)
    - Unit parsing for power, frequency, impedance, dimensions
    - Category and series detection
    - Data validation and cleaning
    """
    
    # Regex patterns for unit parsing
    POWER_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*[Ww](?:atts?)?', re.IGNORECASE)
    POWER_COMPLEX_PATTERN = re.compile(
        r'(\d+)\s*[Ww]\s*(?:LF|passive)?\s*\+?\s*(\d+)\s*[Ww]\s*(?:HF|bi-?amp)?',
        re.IGNORECASE
    )
    
    FREQ_RANGE_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(Hz|kHz)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(Hz|kHz)',
        re.IGNORECASE
    )
    
    IMPEDANCE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:Ω|ohms?)', re.IGNORECASE)
    
    VOLTAGE_PATTERN = re.compile(r'(70V|100V|Low-?Z)', re.IGNORECASE)
    
    DIMENSION_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*[×x]\s*(\d+(?:\.\d+)?)\s*[×x]\s*(\d+(?:\.\d+)?)\s*(mm|in|cm)?',
        re.IGNORECASE
    )
    
    WEIGHT_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(kg|lb|lbs|g)',
        re.IGNORECASE
    )
    
    # Model range patterns (e.g., AM10/60/80, DM3SE)
    MODEL_RANGE_PATTERN = re.compile(r'^([A-Z]+\d+)/(\d+(?:/\d+)*)$', re.IGNORECASE)
    
    # Category detection from page/table headers
    CATEGORY_KEYWORDS = {
        'loudspeaker': ['loudspeaker', 'speaker', 'surface-mount', 'ceiling', 'pendant'],
        'amplifier': ['amplifier', 'power amp', 'zone amp', 'mixer amp'],
        'controller': ['controller', 'control center', 'controlspace'],
        'subwoofer': ['subwoofer', 'sub', 'bass'],
        'system': ['system package', 'audiopack', 'complete system'],
    }
    
    # Series detection
    SERIES_KEYWORDS = {
        'DesignMax': ['designmax', 'dm'],
        'FreeSpace': ['freespace', 'fs'],
        'ArenaMatch': ['arenamatch', 'am'],
        'EdgeMax': ['edgemax', 'em'],
        'PowerSpace': ['powerspace', 'p4', 'p2'],
        'Veritas': ['veritas'],
        'ControlCenter': ['controlcenter', 'cc-'],
        'ControlSpace': ['controlspace'],
    }
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the normalizer."""
        self.cache_dir = cache_dir or settings.processed_path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def normalize(
        self, 
        extraction_results: list[dict],
    ) -> NormalizationResult:
        """
        Normalize extracted table data into product records.
        
        Args:
            extraction_results: List of extraction results from PDFExtractor
            
        Returns:
            NormalizationResult with normalized products
        """
        logger.info(f"Normalizing {len(extraction_results)} extraction results")
        
        products = []
        errors = []
        stats = {
            "tables_processed": 0,
            "rows_processed": 0,
            "products_created": 0,
            "rows_exploded": 0,
        }
        
        for extraction in extraction_results:
            pdf_source = extraction.get('pdf_source', 'unknown')
            
            for table in extraction.get('tables', []):
                stats["tables_processed"] += 1
                
                # Detect category from table context
                table_category = self._detect_category(table)
                table_series = self._detect_series(table)
                
                headers = table.get('headers', [])
                
                for row in table.get('rows', []):
                    stats["rows_processed"] += 1
                    
                    try:
                        # Find model name column
                        model_name = self._extract_model_name(row, headers)
                        
                        if not model_name:
                            continue
                        
                        # Explode model ranges
                        exploded_models = self._explode_model_range(model_name)
                        stats["rows_exploded"] += len(exploded_models) - 1
                        
                        for model in exploded_models:
                            # Parse specifications
                            specs = self._parse_specs(row, model)
                            
                            # Add category and series
                            specs['category'] = table_category
                            specs['series'] = table_series or self._detect_series_from_model(model)
                            
                            # Detect voltage type
                            specs['voltage_type'] = self._detect_voltage_type(row)
                            
                            # Create raw text for embeddings
                            raw_text = self._create_raw_text(model, specs)
                            
                            product = NormalizedProduct(
                                model_name=model,
                                category=table_category,
                                series=specs['series'] or 'Unknown',
                                specs=specs,
                                pdf_source=pdf_source,
                                page_number=table.get('page_number', 0),
                                raw_text=raw_text,
                            )
                            
                            products.append(product)
                            stats["products_created"] += 1
                            
                    except Exception as e:
                        error_msg = f"Error normalizing row: {e}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
        
        result = NormalizationResult(
            products=products,
            errors=errors,
            stats=stats,
        )
        
        # Cache the result
        self._save_to_cache(result)
        
        logger.info(
            f"Normalization complete: {stats['products_created']} products from "
            f"{stats['rows_processed']} rows ({stats['rows_exploded']} exploded)"
        )
        
        return result
    
    def _extract_model_name(self, row: dict, headers: list[str]) -> Optional[str]:
        """Extract model name from row data."""
        # Common model name column patterns
        model_columns = [
            'model', 'model_name', 'product', 'name', 
            'model_number', 'product_code', 'sku'
        ]
        
        for col in model_columns:
            for header in headers:
                if col in header.lower():
                    value = row.get(header)
                    if value:
                        return self._clean_model_name(str(value))
        
        # If no explicit model column, look for patterns in values
        for key, value in row.items():
            if value and self._looks_like_model_name(str(value)):
                return self._clean_model_name(str(value))
        
        return None
    
    def _clean_model_name(self, name: str) -> str:
        """Clean and normalize model name."""
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove common prefixes/suffixes
        name = re.sub(r'^(Bose\s+)?Professional\s*', '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def _looks_like_model_name(self, value: str) -> bool:
        """Check if a value looks like a Bose model name."""
        # Bose model patterns: AM10/60, DM3SE, FS2SE, IZA 250-LZ, etc.
        patterns = [
            r'^[A-Z]{2,4}\d+/?\d*',  # AM10, DM3SE, FS2SE
            r'^[A-Z]+\s*\d+',  # IZA 250
            r'^P\d{4}[A-Z]?',  # P4300A
            r'^CC-\d',  # CC-1, CC-2D
        ]
        
        for pattern in patterns:
            if re.match(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _explode_model_range(self, model_name: str) -> list[str]:
        """
        Explode model range into individual models.
        
        Examples:
            "AM10/60/80" → ["AM10/60", "AM10/80"]
            "AM10/60" → ["AM10/60"]
            "DM3SE" → ["DM3SE"]
        """
        # Pattern: BASE/VAR1/VAR2/... where VAR are just numbers
        match = self.MODEL_RANGE_PATTERN.match(model_name)
        
        if not match:
            return [model_name]
        
        base = match.group(1)  # e.g., "AM10"
        variants_str = match.group(2)  # e.g., "60/80" or "60/80/100"
        
        variants = variants_str.split('/')
        
        if len(variants) <= 1:
            return [model_name]
        
        # Create individual model names
        # Pattern: AM10/60, AM10/80 (not AM10/60/80 which stays together)
        return [f"{base}/{v}" for v in variants]
    
    def _parse_specs(self, row: dict, model_name: str) -> dict[str, Any]:
        """Parse and normalize product specifications."""
        specs = {}
        
        for key, value in row.items():
            if value is None:
                continue
            
            value_str = str(value).strip()
            if not value_str:
                continue
            
            # Normalize key
            norm_key = self._normalize_key(key)
            
            # Parse based on key type
            if 'power' in norm_key.lower() or 'watt' in norm_key.lower():
                parsed = self._parse_power(value_str)
                if parsed:
                    specs['power_watts'] = parsed.get('total')
                    if 'lf' in parsed:
                        specs['power_lf_watts'] = parsed['lf']
                    if 'hf' in parsed:
                        specs['power_hf_watts'] = parsed['hf']
                    specs['power_raw'] = value_str
                continue
            
            if 'freq' in norm_key.lower() or 'response' in norm_key.lower():
                parsed = self._parse_frequency_range(value_str)
                if parsed:
                    specs['freq_min_hz'] = parsed.get('min')
                    specs['freq_max_hz'] = parsed.get('max')
                    specs['freq_raw'] = value_str
                continue
            
            if 'impedance' in norm_key.lower():
                parsed = self._parse_impedance(value_str)
                if parsed:
                    specs['impedance_ohms'] = parsed
                    specs['impedance_raw'] = value_str
                continue
            
            if 'dimension' in norm_key.lower() or 'size' in norm_key.lower():
                parsed = self._parse_dimensions(value_str)
                if parsed:
                    specs['dimensions'] = parsed
                    specs['dimensions_raw'] = value_str
                continue
            
            if 'weight' in norm_key.lower():
                parsed = self._parse_weight(value_str)
                if parsed:
                    specs['weight_kg'] = parsed
                    specs['weight_raw'] = value_str
                continue
            
            if 'sensitivity' in norm_key.lower() or 'spl' in norm_key.lower():
                db_match = re.search(r'(\d+(?:\.\d+)?)\s*dB', value_str)
                if db_match:
                    specs['sensitivity_db'] = float(db_match.group(1))
                    specs['sensitivity_raw'] = value_str
                continue
            
            if 'coverage' in norm_key.lower():
                specs['coverage'] = value_str
                continue
            
            if 'driver' in norm_key.lower() or 'component' in norm_key.lower():
                specs['driver_components'] = value_str
                continue
            
            if 'color' in norm_key.lower():
                specs['color_options'] = value_str
                continue
            
            if 'environment' in norm_key.lower():
                specs['environmental'] = value_str
                continue
            
            if 'product_code' in norm_key.lower() or 'sku' in norm_key.lower():
                specs['product_codes'] = value_str
                continue
            
            # Store other specs as-is
            specs[norm_key] = value_str
        
        return specs
    
    def _normalize_key(self, key: str) -> str:
        """Normalize a specification key."""
        # Convert to lowercase and replace spaces/special chars with underscores
        key = re.sub(r'[^\w\s]', '', key.lower())
        key = re.sub(r'\s+', '_', key).strip('_')
        return key
    
    def _parse_power(self, value: str) -> Optional[dict]:
        """
        Parse power values from various formats.
        
        Examples:
            "125 W" → {"total": 125}
            "750 W passive" → {"total": 750}
            "600 W LF + 150 W HF bi-amp" → {"lf": 600, "hf": 150, "total": 750}
            "2 × 160 W" → {"total": 320}
        """
        # Check for complex LF + HF pattern
        complex_match = self.POWER_COMPLEX_PATTERN.search(value)
        if complex_match:
            lf = int(complex_match.group(1))
            hf = int(complex_match.group(2))
            return {"lf": lf, "hf": hf, "total": lf + hf}
        
        # Check for multiplied power (2 × 160 W)
        mult_match = re.search(r'(\d+)\s*[×x]\s*(\d+)\s*W', value, re.IGNORECASE)
        if mult_match:
            multiplier = int(mult_match.group(1))
            watts = int(mult_match.group(2))
            return {"total": multiplier * watts}
        
        # Simple power pattern
        simple_match = self.POWER_PATTERN.search(value)
        if simple_match:
            return {"total": int(float(simple_match.group(1)))}
        
        return None
    
    def _parse_frequency_range(self, value: str) -> Optional[dict]:
        """
        Parse frequency range values.
        
        Examples:
            "95 Hz - 16 kHz" → {"min": 95, "max": 16000}
            "65 Hz – 20 kHz" → {"min": 65, "max": 20000}
        """
        match = self.FREQ_RANGE_PATTERN.search(value)
        if not match:
            return None
        
        min_val = float(match.group(1))
        min_unit = match.group(2).lower()
        max_val = float(match.group(3))
        max_unit = match.group(4).lower()
        
        # Convert to Hz
        if min_unit == 'khz':
            min_val *= 1000
        if max_unit == 'khz':
            max_val *= 1000
        
        return {"min": int(min_val), "max": int(max_val)}
    
    def _parse_impedance(self, value: str) -> Optional[float]:
        """
        Parse impedance value.
        
        Examples:
            "8 ohms" → 8.0
            "16 Ω in bypass" → 16.0
        """
        match = self.IMPEDANCE_PATTERN.search(value)
        if match:
            return float(match.group(1))
        return None
    
    def _parse_dimensions(self, value: str) -> Optional[dict]:
        """
        Parse dimension values.
        
        Examples:
            "182 × 113 × 114 mm" → {"h": 182, "w": 113, "d": 114, "unit": "mm"}
        """
        match = self.DIMENSION_PATTERN.search(value)
        if not match:
            return None
        
        return {
            "h": float(match.group(1)),
            "w": float(match.group(2)),
            "d": float(match.group(3)),
            "unit": match.group(4) or "mm",
        }
    
    def _parse_weight(self, value: str) -> Optional[float]:
        """
        Parse weight value and convert to kg.
        
        Examples:
            "1.43 kg" → 1.43
            "3.15 lb" → 1.43 (converted)
        """
        match = self.WEIGHT_PATTERN.search(value)
        if not match:
            return None
        
        weight = float(match.group(1))
        unit = match.group(2).lower()
        
        # Convert to kg
        if unit in ('lb', 'lbs'):
            weight *= 0.453592
        elif unit == 'g':
            weight /= 1000
        
        return round(weight, 2)
    
    def _detect_category(self, table: dict) -> str:
        """Detect product category from table context."""
        # Check headers and raw data for category keywords
        text_to_check = ' '.join([
            ' '.join(table.get('headers', [])),
            str(table.get('raw_data', [])),
        ]).lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return category
        
        return 'unknown'
    
    def _detect_series(self, table: dict) -> Optional[str]:
        """Detect product series from table context."""
        text_to_check = ' '.join([
            ' '.join(table.get('headers', [])),
            str(table.get('raw_data', [])),
        ]).lower()
        
        for series, keywords in self.SERIES_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return series
        
        return None
    
    def _detect_series_from_model(self, model_name: str) -> Optional[str]:
        """Detect series from model name pattern."""
        model_lower = model_name.lower()
        
        series_patterns = {
            'DesignMax': r'^dm\d',
            'FreeSpace': r'^fs\d',
            'ArenaMatch': r'^am\d',
            'EdgeMax': r'^em\d',
            'PowerSpace': r'^p[24]\d{3}',
            'ControlCenter': r'^cc-\d',
        }
        
        for series, pattern in series_patterns.items():
            if re.match(pattern, model_lower):
                return series
        
        return None
    
    def _detect_voltage_type(self, row: dict) -> Optional[str]:
        """Detect voltage type from row data."""
        row_text = ' '.join(str(v) for v in row.values()).lower()
        
        if '70v' in row_text and '100v' in row_text:
            return '70V/100V'
        elif '70v' in row_text:
            return '70V'
        elif '100v' in row_text:
            return '100V'
        elif 'low-z' in row_text or 'low z' in row_text:
            return 'Low-Z'
        
        return None
    
    def _create_raw_text(self, model_name: str, specs: dict) -> str:
        """Create raw text for embedding generation."""
        parts = [f"Model: {model_name}"]
        
        if specs.get('category'):
            parts.append(f"Category: {specs['category']}")
        
        if specs.get('series'):
            parts.append(f"Series: {specs['series']}")
        
        if specs.get('power_watts'):
            parts.append(f"Power: {specs['power_watts']}W")
        
        if specs.get('freq_min_hz') and specs.get('freq_max_hz'):
            parts.append(f"Frequency: {specs['freq_min_hz']}Hz - {specs['freq_max_hz']}Hz")
        
        if specs.get('impedance_ohms'):
            parts.append(f"Impedance: {specs['impedance_ohms']} ohms")
        
        if specs.get('coverage'):
            parts.append(f"Coverage: {specs['coverage']}")
        
        if specs.get('driver_components'):
            parts.append(f"Drivers: {specs['driver_components']}")
        
        if specs.get('voltage_type'):
            parts.append(f"Voltage: {specs['voltage_type']}")
        
        return ' | '.join(parts)
    
    def _save_to_cache(self, result: NormalizationResult) -> None:
        """Save normalization result to cache."""
        output_path = settings.normalized_cache
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved normalized products to: {output_path}")
    
    async def load_from_cache(self) -> Optional[NormalizationResult]:
        """Load normalization result from cache."""
        cache_path = settings.normalized_cache
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            products = [NormalizedProduct(**p) for p in data.get('products', [])]
            
            return NormalizationResult(
                products=products,
                errors=data.get('errors', []),
                stats=data.get('stats', {}),
            )
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return None
