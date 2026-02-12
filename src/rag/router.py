"""
Query Router for intent classification.
Uses Ollama LLM to classify queries into DIRECT_LOOKUP, SEMANTIC_SEARCH, or CALCULATION.
"""

import logging
import re
from enum import Enum
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries the system can handle."""
    DIRECT_LOOKUP = "direct_lookup"      # "What's the power of AM10/60?"
    SEMANTIC_SEARCH = "semantic_search"  # "Find ceiling speakers for conference rooms"
    CALCULATION = "calculation"          # "Can I connect 8 speakers to 70V?"
    PURCHASE_INTENT = "purchase_intent"  # "How much is it?"
    DOMAIN_VIOLATION = "domain_violation" # "Compare to Sonos"
    UNKNOWN = "unknown"


class QueryRouter:
    """
    Classifies user queries to determine the appropriate handling strategy.
    
    Uses a combination of:
    1. Rule-based pattern matching (fast, no LLM)
    2. Ollama LLM classification (when rules are insufficient)
    """
    
    # Rule-based patterns for fast classification
    DIRECT_LOOKUP_PATTERNS = [
        r"what(?:'s| is) the .* of (\w+[-/]?\w*)",  # "What's the power of AM10/60?"
        r"(?:get|show|tell me) (?:the )?.* (?:for|of) (\w+[-/]?\w*)",
        r"(\w+[-/]\w+) (?:specs|specifications|details)",
        r"specs (?:for|of) (\w+[-/]?\w*)",
        r"(\w+) (?:power|specs|frequency|impedance|sensitivity|coverage|weight)",
    ]
    
    CALCULATION_PATTERNS = [
        r"can I connect",
        r"how many .* can I",
        r"will .* work with",
        r"calculate",
        r"what(?:'s| is) the total",
        r"(\d+)\s*(?:×|x)\s*(\d+)\s*W",  # "4 x 30W"
        r"(\d+)\s*speakers?\s*(?:at|@)\s*(\d+)\s*W",
        r"transformer",
        r"impedance.*(?:series|parallel)",
    ]
    
    SEMANTIC_SEARCH_PATTERNS = [
        r"find",
        r"search",
        r"recommend",
        r"suggest",
        r"looking for",
        r"best .* for",
        r"which .* should",
        r"suitable for",
        r"good for",
    ]

    # Purchase intent patterns
    PURCHASE_INTENT_PATTERNS = [
        r"price",
        r"cost",
        r"how much",
        r"buy",
        r"purchase",
        r"stock",
        r"availability",
        r"where to get",
        r"ordering",
        r"quote",
        r"discount",
        r"deal",
        r"sale",
    ]

    # Domain violation patterns (Competitors)
    DOMAIN_VIOLATION_PATTERNS = [
        r"sonos",
        r"jbl",
        r"yamaha",
        r"qsc",
        r"crestron",
        r"extron",
        r"biamp",
        r"crown",
        r"lab.gruppen",
    ]
    
    # LLM classification prompt
    CLASSIFICATION_PROMPT = """You are classifying user queries about Bose professional audio products.

Classify this query into exactly one category:
- DIRECT_LOOKUP: Asking for specific specs of a known product (e.g., "What's the power of AM10/60?")
- SEMANTIC_SEARCH: Looking for products matching criteria (e.g., "Find 70V speakers for conference rooms")
- CALCULATION: Math/electrical calculations (e.g., "Can I connect 4x30W speakers to 150W transformer?")

Query: {query}

Respond with ONLY one word: DIRECT_LOOKUP, SEMANTIC_SEARCH, or CALCULATION"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        use_llm: bool = True,
    ):
        """
        Initialize the query router.
        
        Args:
            base_url: Ollama API base URL
            model: LLM model name
            use_llm: Whether to use LLM for ambiguous queries
        """
        self.base_url = (base_url or settings.ollama_base_url).rstrip('/')
        self.model = model or settings.ollama_llm_model
        self.use_llm = use_llm
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0),
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _rule_based_classify(self, query: str) -> Optional[QueryType]:
        """
        Fast rule-based classification using regex patterns.
        
        Returns:
            QueryType if confidently classified, None otherwise
        """
        query_lower = query.lower()
        
        # Check for calculation patterns first (most specific)
        for pattern in self.CALCULATION_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryType.CALCULATION
        
        # Check for direct lookup (model name in query)
        for pattern in self.DIRECT_LOOKUP_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryType.DIRECT_LOOKUP
        
        # Check for semantic search
        for pattern in self.SEMANTIC_SEARCH_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryType.SEMANTIC_SEARCH
        
        return None
    
    async def _llm_classify(self, query: str) -> QueryType:
        """
        Use Ollama LLM for classification when rules are insufficient.
        
        Args:
            query: User query to classify
            
        Returns:
            Classified QueryType
        """
        try:
            client = await self._get_client()
            
            prompt = self.CLASSIFICATION_PROMPT.format(query=query)
            
            response = await client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Very low for consistent classification
                        "num_predict": 10,
                    },
                },
            )
            
            if response.status_code != 200:
                logger.error(f"LLM classification failed: {response.status_code}")
                return QueryType.SEMANTIC_SEARCH  # Default fallback
            
            data = response.json()
            result = data.get('response', '').strip().upper()
            
            # Parse result
            if 'DIRECT' in result or 'LOOKUP' in result:
                return QueryType.DIRECT_LOOKUP
            elif 'CALCULATION' in result or 'CALC' in result:
                return QueryType.CALCULATION
            elif 'SEMANTIC' in result or 'SEARCH' in result:
                return QueryType.SEMANTIC_SEARCH
            else:
                logger.warning(f"Unexpected LLM response: {result}")
                return QueryType.SEMANTIC_SEARCH
                
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return QueryType.SEMANTIC_SEARCH
    
    async def classify(self, query: str) -> QueryType:
        """
        Classify a user query into the appropriate type.
        
        Uses rule-based matching first, falls back to LLM for ambiguous cases.
        
        Args:
            query: User query to classify
            
        Returns:
            QueryType indicating how to handle the query
        """
        if not query or not query.strip():
            return QueryType.UNKNOWN
        
        query = query.strip()
        
        # Layer 1 Check: Purchase Intent
        if self._check_purchase_intent(query):
            logger.info(f"Purchase intent detected: {query}")
            return QueryType.PURCHASE_INTENT
            
        # Layer 1 Check: Domain Violation
        if self._check_domain_violation(query):
            logger.info(f"Domain violation detected: {query}")
            return QueryType.DOMAIN_VIOLATION
        
        # Try rule-based classification first (fast)
        rule_result = self._rule_based_classify(query)
        if rule_result is not None:
            logger.debug(f"Rule-based classification: {query[:50]} -> {rule_result.value}")
            return rule_result
        
        # Fall back to LLM if enabled
        if self.use_llm:
            llm_result = await self._llm_classify(query)
            logger.debug(f"LLM classification: {query[:50]} -> {llm_result.value}")
            return llm_result
        
        # Default to semantic search
        return QueryType.SEMANTIC_SEARCH
    
    def extract_model_name(self, query: str) -> Optional[str]:
        """
        Extract product model name from query for direct lookup.
        
        Args:
            query: User query
            
        Returns:
            Extracted model name or None
        """
        # Bose model patterns
        patterns = [
            r'\b(AM\d+/\d+(?:/\d+)?)\b',   # AM10/60, AM10/60/80
            r'\b(DM\d+[A-Z]*(?:-[A-Z]+)?)\b',  # DM3C, DM3SE, DM2C-LP, DM8C-SUB
            r'\b(FS\d+[A-Z]*)\b',          # FS2SE, FS4SE
            r'\b(EM\d+(?:-LP)?)\b',        # EM90, EM90-LP
            r'\b(IZA\s*\d+-?\w*)\b',       # IZA 250-LZ
            r'\b(PS[X]?\d{3,4}[A-Z]*)\b',  # PS404D, PSX1204D
            r'\b(P\d{4}[A-Z]?)\b',         # P4300A
            r'\b(CC-\d+D?)\b',             # CC-1, CC-2D
            r'\b(\d{3,4}B[LH])\b',         # 250BL, 1100BH
            r'\b(VB[\-]?[S1]?)\b',          # VB1, VB-S
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def extract_filters(self, query: str) -> dict:
        """
        Extract filter parameters from query for SQL WHERE clause.
        
        Args:
            query: User query
            
        Returns:
            Dict of filter parameters
        """
        filters = {}
        query_lower = query.lower()
        
        # Power filters
        power_match = re.search(r'(?:over|above|more than|>)\s*(\d+)\s*W', query, re.I)
        if power_match:
            filters['min_watts'] = int(power_match.group(1))
        
        power_match = re.search(r'(?:under|below|less than|<)\s*(\d+)\s*W', query, re.I)
        if power_match:
            filters['max_watts'] = int(power_match.group(1))
        
        # Voltage type
        if '70v' in query_lower and '100v' in query_lower:
            filters['voltage_type'] = '70V/100V'
        elif '70v' in query_lower:
            filters['voltage_type'] = '70V'
        elif '100v' in query_lower:
            filters['voltage_type'] = '100V'
        elif 'low-z' in query_lower or 'low z' in query_lower:
            filters['voltage_type'] = 'Low-Z'
        
        # Category
        if any(kw in query_lower for kw in ['speaker', 'loudspeaker']):
            filters['category'] = 'loudspeaker'
        elif any(kw in query_lower for kw in ['amp', 'amplifier']):
            filters['category'] = 'amplifier'
        elif 'controller' in query_lower:
            filters['category'] = 'controller'
        elif 'sub' in query_lower:
            filters['category'] = 'subwoofer'
        
        # Series
        series_keywords = {
            'designmax': 'DesignMax',
            'freespace': 'FreeSpace',
            'arenamatch': 'ArenaMatch',
            'edgemax': 'EdgeMax',
            'powerspace': 'PowerSpace',
        }
        for kw, series in series_keywords.items():
            if kw in query_lower:
                filters['series'] = series
                break
        
        return filters
    
    def extract_calculation_params(self, query: str) -> dict:
        """
        Extract parameters for electrical calculations.
        
        Args:
            query: User query
            
        Returns:
            Dict of calculation parameters
        """
        params = {}
        
        # Extract speaker wattages: "4 speakers at 30W" or "4x30W" or "6 x 30W speakers"
        speaker_match = re.search(
            r'(\d+)\s*(?:×|x|speakers?\s*(?:at|@)?)\s*(\d+)\s*W',
            query, re.IGNORECASE
        )
        if speaker_match:
            count = int(speaker_match.group(1))
            watts = int(speaker_match.group(2))
            params['speakers'] = [watts] * count
        
        # Extract transformer capacity: "150W transformer" or "transformer ... 150W"
        transformer_match = re.search(
            r'(\d+)\s*W\s*(?:transformer|amp|amplifier)',
            query, re.IGNORECASE
        )
        if transformer_match:
            params['transformer_watts'] = int(transformer_match.group(1))
        
        # Transformer recommendation: "What transformer do I need for 200W"
        if 'transformer' in query.lower() and 'transformer_watts' not in params:
            watt_match = re.search(r'(\d+)\s*W', query, re.IGNORECASE)
            if watt_match:
                params['recommend_transformer_for'] = int(watt_match.group(1))
        
        # Extract impedances with multiplier: "3 x 8 ohm" or "3x8Ω"
        impedance_mult_match = re.search(
            r'(\d+)\s*(?:×|x)\s*(\d+)\s*(?:Ω|ohm)',
            query, re.IGNORECASE
        )
        if impedance_mult_match:
            count = int(impedance_mult_match.group(1))
            ohms = float(impedance_mult_match.group(2))
            params['impedances'] = [ohms] * count
        else:
            # Extract individual impedances: "4 ohm and 8 ohm"
            impedance_match = re.findall(r'(\d+)\s*(?:Ω|ohm)', query, re.IGNORECASE)
            if impedance_match:
                params['impedances'] = [float(z) for z in impedance_match]
        
        # Connection type
        if 'series' in query.lower():
            params['connection'] = 'series'
        elif 'parallel' in query.lower():
            params['connection'] = 'parallel'
        
        return params
    
    def _check_purchase_intent(self, query: str) -> bool:
        """Check if query indicates purchase intent."""
        query_lower = query.lower()
        for pattern in self.PURCHASE_INTENT_PATTERNS:
            if re.search(r'\b' + pattern + r'\b', query_lower, re.IGNORECASE):
                return True
        return False

    def _check_domain_violation(self, query: str) -> bool:
        """Check if query mentions competitor brands."""
        query_lower = query.lower()
        for pattern in self.DOMAIN_VIOLATION_PATTERNS:
            if re.search(r'\b' + pattern + r'\b', query_lower, re.IGNORECASE):
                return True
        return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
