"""
Product Normalizer for Bose specifications.
Handles transposed tables where columns = products, rows = specs.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

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
    watts_int: Optional[int] = None
    ohms_int: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_db_record(self) -> dict:
        return {
            "model_name": self.model_name,
            "specs": json.dumps(self.specs),
            "pdf_source": self.pdf_source,
            "page_number": self.page_number,
            "raw_text": self.raw_text,
        }


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

    Bose tables are TRANSPOSED:
      - headers[0] = spec label key (e.g. "Driver_Components")
      - headers[1:] = product column names
      - Each row dict: {label_key: "Power Handling", product_col: "20W", ...}
      - raw_data[0] has cleaner model names like "FreeSpace.FS2SE"
    """

    # Category detection from category_hint
    CATEGORY_MAP = {
        "loudspeaker": ["loudspeaker", "speaker", "surface-mount", "in-ceiling",
                        "pendant", "utility"],
        "subwoofer": ["subwoofer", "sub"],
        "amplifier": ["amplifier", "powershare", "powerspace"],
        "controller": ["controller", "controlcenter"],
        "mixer": ["mixer"],
        "signal_processor": ["signal processor", "esp", "ex"],
    }

    def __init__(self):
        self.output_path = settings.processed_path / "normalized_products.json"

    async def normalize(self, extraction_results: list[dict]) -> NormalizationResult:
        """
        Normalize extraction results. Each result has pdf_source and tables.
        Tables are transposed: columns = products, rows = specs.
        """
        logger.info(f"Normalizing {len(extraction_results)} extraction results")

        all_products: list[NormalizedProduct] = []
        all_errors: list[str] = []
        models_exploded = 0

        for ext_result in extraction_results:
            pdf_source = ext_result.get("pdf_source", "unknown")
            tables = ext_result.get("tables", [])

            for table in tables:
                try:
                    products, exploded = self._normalize_table(table, pdf_source)
                    all_products.extend(products)
                    models_exploded += exploded
                except Exception as e:
                    err = f"Error normalizing table from {pdf_source} p{table.get('page_number', '?')}: {e}"
                    logger.error(err)
                    all_errors.append(err)

        # Save output
        self._save_output(all_products)

        result = NormalizationResult(
            products=all_products,
            errors=all_errors,
            stats={
                "total_products": len(all_products),
                "rows_exploded": models_exploded,
                "tables_processed": sum(len(r.get("tables", [])) for r in extraction_results),
            },
        )

        logger.info(
            f"Normalization complete: {len(all_products)} products "
            f"from {result.stats['tables_processed']} tables "
            f"({models_exploded} exploded)"
        )
        return result

    def _normalize_table(
        self, table: dict, pdf_source: str
    ) -> tuple[list[NormalizedProduct], int]:
        """
        Normalize a single transposed table.

        Returns (products, exploded_count)
        """
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        raw_data = table.get("raw_data", [])
        category_hint = table.get("category_hint", "")
        page_number = table.get("page_number", 0)

        if len(headers) < 2 or not rows:
            return [], 0

        # headers[0] is the spec label key (e.g. "Driver_Components")
        label_key = headers[0]
        # headers[1:] are product columns
        product_columns = headers[1:]

        # Try to get cleaner model names from raw_data[0]
        clean_names = {}
        if raw_data and len(raw_data) > 0:
            raw_header_row = raw_data[0]
            for i, col in enumerate(product_columns):
                # raw_data[0] index offset: raw_data[0][0] is empty, [1] matches headers[1], etc.
                raw_idx = i + 1
                if raw_idx < len(raw_header_row) and raw_header_row[raw_idx]:
                    clean_names[col] = raw_header_row[raw_idx]

        # Detect category from the category_hint
        category = self._detect_category(category_hint)

        products: list[NormalizedProduct] = []
        exploded = 0

        for col in product_columns:
            model_name = clean_names.get(col, col)

            # Detect series per-product from model name, fallback to hint
            series = self._detect_series(category_hint, model_name)

            # Build specs dict: iterate all rows, key=row's label, value=row's column value
            specs: dict[str, Any] = {}
            for row in rows:
                spec_name = row.get(label_key, "")
                spec_value = row.get(col, "")
                if spec_name and spec_value and str(spec_value).strip() not in ("", "-"):
                    specs[spec_name] = str(spec_value).strip()

            if not specs:
                continue

            # Extract watts_int and ohms_int
            watts_int = self._extract_watts(specs)
            ohms_int = self._extract_ohms(specs)

            # Build raw_text summary
            raw_text = f"{model_name} | {category} | {series}"
            for key in ["Power Handling (Long-term)", "Sensitivity (SPL/1W@1m)", "Driver Components"]:
                if key in specs:
                    raw_text += f" | {key}: {specs[key]}"

            # Explode slash-separated model names
            model_names = self._explode_model(model_name)
            if len(model_names) > 1:
                exploded += len(model_names) - 1

            for name in model_names:
                products.append(NormalizedProduct(
                    model_name=name.strip(),
                    category=category,
                    series=series,
                    specs=specs,
                    pdf_source=pdf_source,
                    page_number=page_number,
                    raw_text=raw_text,
                    watts_int=watts_int,
                    ohms_int=ohms_int,
                ))

        return products, exploded

    def _explode_model(self, model_name: str) -> list[str]:
        """
        Split slash-separated model names.
        e.g. "AM10/60 / AM10/80" -> ["AM10/60", "AM10/80"]
        e.g. "AMU108 / AMU108-120" -> ["AMU108", "AMU108-120"]
        But NOT "70V/100V" or "H × V" patterns.
        """
        # Only split on " / " (space-slash-space) to avoid splitting "70V/100V"
        if " / " in model_name:
            parts = [p.strip() for p in model_name.split(" / ")]
            # Sanity check: each part should look like a model name (has letters + numbers)
            if all(re.search(r'[A-Z]', p) and re.search(r'\d', p) for p in parts):
                return parts
        return [model_name]

    def _extract_watts(self, specs: dict) -> Optional[int]:
        """Extract integer watts from Power Handling spec."""
        for key in specs:
            if "power" in key.lower() or "watt" in key.lower():
                match = re.search(r'(\d+)\s*[Ww]', specs[key])
                if match:
                    return int(match.group(1))
        return None

    def _extract_ohms(self, specs: dict) -> Optional[int]:
        """Extract integer ohms from Nominal Impedance spec."""
        for key in specs:
            if "impedance" in key.lower():
                match = re.search(r'(\d+)\s*(?:Ω|Ω|ohm)', specs[key], re.IGNORECASE)
                if match:
                    return int(match.group(1))
        return None

    def _detect_category(self, category_hint: str) -> str:
        """Detect product category from the page category hint."""
        hint_lower = category_hint.lower()
        for category, keywords in self.CATEGORY_MAP.items():
            if any(kw in hint_lower for kw in keywords):
                return category
        return "loudspeaker"  # default

    def _detect_series(self, category_hint: str, model_name: str = "") -> str:
        """Detect product series from category hint or a specific model name."""
        known_series = [
            "DesignMax", "EdgeMax", "FreeSpace", "Panaray", "RoomMatch",
            "ShowMatch", "ArenaMatch", "PowerShare", "PowerSpace",
            "ControlCenter", "ControlSpace",
        ]

        # Try from the model name first (most specific)
        if model_name:
            for s in known_series:
                if s.lower() in model_name.lower():
                    return s
            if "." in model_name:
                prefix = model_name.split(".")[0]
                for s in known_series:
                    if s.lower() == prefix.lower():
                        return s

        # Try from category_hint
        hint_upper = category_hint.upper()
        for s in known_series:
            if s.upper() in hint_upper:
                return s

        return "Unknown"

    def _save_output(self, products: list[NormalizedProduct]) -> None:
        """Save normalized products to JSON file."""
        output = {"products": [p.to_dict() for p in products]}
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved normalized products to: {self.output_path}")
