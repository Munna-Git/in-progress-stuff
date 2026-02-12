"""
Answer Generator with citations.
Uses Ollama LLM to generate answers based on retrieved product data.
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import httpx

from src.config import settings
from src.rag.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A citation reference to source data."""
    model_name: str
    field: str
    value: Any
    pdf_source: Optional[str] = None


@dataclass
class GeneratedAnswer:
    """Generated answer with citations and metadata."""
    answer: str
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0
    query_type: str = ""
    products_used: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "citations": [asdict(c) for c in self.citations],
            "confidence": self.confidence,
            "query_type": self.query_type,
            "products_used": self.products_used,
        }


class AnswerGenerator:
    """
    Generate natural language answers with citations.
    
    Uses Ollama LLM to synthesize answers from retrieved product data
    while maintaining factual accuracy through citations.
    """
    
    # Answer generation prompt template
    GENERATION_PROMPT = """You are a Bose professional audio product expert.
You are a technical support interface. You are prohibited from discussing commercial terms, discounts, or stock levels.
Answer the user's question using ONLY the product data provided below.
Do NOT make up any specifications or information not in the data.
Be concise and factual.
If the answer is not in the data, say "I couldn't find that information in the provided product data."

User Question: {query}

Product Data:
{product_data}

Instructions:
1. Answer the question directly
2. Include specific values from the data
3. Mention model names when relevant
4. Keep answer under 150 words

Answer:"""

    # Direct lookup template (no LLM needed)
    DIRECT_ANSWER_TEMPLATE = """Based on the specifications for **{model_name}**:

{specs_text}

*Source: {pdf_source}*"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the answer generator.
        
        Args:
            base_url: Ollama API base URL
            model: LLM model name
        """
        self.base_url = (base_url or settings.ollama_base_url).rstrip('/')
        self.model = model or settings.ollama_llm_model
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(60.0),
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def generate_direct_answer(
        self,
        query: str,
        result: RetrievalResult,
    ) -> GeneratedAnswer:
        """
        Generate answer for direct lookup queries.
        
        No LLM needed - just format the specs.
        
        Args:
            query: Original user query
            result: Retrieved product data
            
        Returns:
            Generated answer with citations
        """
        specs = result.specs
        citations = []
        specs_lines = []
        
        # Map normalized keys AND raw keys to display labels
        # Format: (source_key, label, unit, normalized_key)
        spec_mappings = [
            ('power_watts', 'Power', 'W', 'power_watts'),
            ('Power Handling (Long-term)', 'Power', 'W', 'power_watts'),
            
            ('freq_min_hz', 'Freq Min', 'Hz', 'freq_min_hz'),
            ('freq_max_hz', 'Freq Max', 'Hz', 'freq_max_hz'),
            ('Freq Response (-3 dB) Freq Range (-10 dB)', 'Freq Response', '', 'freq_response'),
            
            ('impedance_ohms', 'Impedance', 'Ω', 'impedance_ohms'),
            ('Nominal Impedance', 'Impedance', 'Ω', 'impedance_ohms'),
            
            ('sensitivity_db', 'Sensitivity', 'dB', 'sensitivity_db'),
            ('Sensitivity (SPL/1W@1m)', 'Sensitivity', 'dB', 'sensitivity_db'),
            
            ('coverage', 'Coverage', '', 'coverage'),
            ('Coverage (H × V, or Conical) 1 kHz - 4 kHz Average', 'Coverage', '', 'coverage'),
            
            ('voltage_type', 'Voltage', '', 'voltage_type'),
            
            ('driver_components', 'Drivers', '', 'driver_components'),
            ('Driver Components', 'Drivers', '', 'driver_components'),
            ('weight_kg', 'Weight', 'kg', 'weight_kg'),
            ('color_options', 'Colors', '', 'color_options'),
            ('environmental', 'Environmental', '', 'environmental'),
        ]
        
        for key, label, unit, norm_key in spec_mappings:
            if key in specs and specs[key] is not None:
                value = specs[key]
                if unit:
                    specs_lines.append(f"- **{label}**: {value} {unit}")
                else:
                    specs_lines.append(f"- **{label}**: {value}")
                
                citations.append(Citation(
                    model_name=result.model_name,
                    field=norm_key,
                    value=value,
                    pdf_source=result.pdf_source,
                ))
        
        specs_text = "\n".join(specs_lines) if specs_lines else "No specifications available"
        
        answer = self.DIRECT_ANSWER_TEMPLATE.format(
            model_name=result.model_name,
            specs_text=specs_text,
            pdf_source=result.pdf_source or "Bose Product Catalog",
        )
        
        return GeneratedAnswer(
            answer=answer,
            citations=citations,
            confidence=1.0,  # Direct lookup is fully confident
            query_type="direct_lookup",
            products_used=[result.model_name],
        )
    
    async def generate_search_answer(
        self,
        query: str,
        results: list[RetrievalResult],
    ) -> GeneratedAnswer:
        """
        Generate answer for semantic search queries using LLM.
        
        Args:
            query: Original user query
            results: Retrieved products
            
        Returns:
            Generated answer with citations
        """
        if not results:
            return GeneratedAnswer(
                answer="I couldn't find any relevant products to answer that query.",
                citations=[],
                confidence=0.0,
                query_type="semantic_search",
                products_used=[],
            )
        
        # Format product data for LLM
        product_data = self._format_products_for_llm(results)
        
        # Generate answer via LLM
        prompt = self.GENERATION_PROMPT.format(
            query=query,
            product_data=product_data,
        )
        
        try:
            client = await self._get_client()
            
            response = await client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 300,
                    },
                },
            )
            
            if response.status_code != 200:
                logger.error(f"LLM generation failed: {response.status_code}")
                return self._fallback_answer(results)
            
            data = response.json()
            answer_text = data.get('response', '').strip()
            
            # Build citations from used products
            citations = []
            products_used = []
            
            for result in results:
                if result.model_name.lower() in answer_text.lower():
                    products_used.append(result.model_name)
                    
                    # Add key spec citations
                    for key in ['power_watts', 'voltage_type', 'category']:
                        if key in result.specs:
                            citations.append(Citation(
                                model_name=result.model_name,
                                field=key,
                                value=result.specs[key],
                                pdf_source=result.pdf_source,
                            ))
            
            # If no products explicitly mentioned, cite all
            if not products_used:
                products_used = [r.model_name for r in results]
            
            # Calculate confidence based on similarity scores
            avg_similarity = sum(r.similarity_score for r in results) / len(results)
            
            return GeneratedAnswer(
                answer=answer_text,
                citations=citations,
                confidence=min(avg_similarity + 0.2, 1.0),
                query_type="semantic_search",
                products_used=products_used,
            )
            
        except Exception as e:
            logger.error(f"Answer generation error: {e}")
            return self._fallback_answer(results)
    
    def generate_calculation_answer(
        self,
        query: str,
        calc_result: dict,
    ) -> GeneratedAnswer:
        """
        Generate answer for calculation queries.
        
        No LLM needed - just format the calculation result.
        
        Args:
            query: Original user query
            calc_result: Result from calculator
            
        Returns:
            Generated answer
        """
        if 'error' in calc_result:
            return GeneratedAnswer(
                answer=f"Calculation error: {calc_result['error']}",
                citations=[],
                confidence=0.0,
                query_type="calculation",
                products_used=[],
            )
        
        # Format based on calculation type
        if 'compatible' in calc_result:
            # 70V compatibility check
            compatible = "✅ Yes" if calc_result['compatible'] else "❌ No"
            answer = f"""**70V Compatibility Check**

{compatible}, this configuration is {"compatible" if calc_result['compatible'] else "NOT compatible"}.

- **Total Load**: {calc_result['total_load']} W
- **Transformer Capacity**: {calc_result['capacity']} W
- **Headroom**: {calc_result['headroom_percent']:.1f}%

{"The total speaker load is within the transformer's capacity." if calc_result['compatible'] else "The total speaker load exceeds the transformer's capacity. Use a larger transformer or reduce speakers."}"""
        
        elif 'total_impedance' in calc_result:
            # Impedance calculation
            answer = f"""**Impedance Calculation**

- **Connection Type**: {calc_result.get('connection', 'unknown').title()}
- **Total Impedance**: {calc_result['total_impedance']:.2f} Ω
- **Speakers**: {calc_result.get('speakers', [])}"""
        
        elif 'total_power' in calc_result:
            # Simple power sum
            answer = f"""**Power Calculation**

- **Total Power**: {calc_result['total_power']} W
- **Speakers**: {calc_result.get('speakers', [])}"""
        
        elif 'recommended_watts' in calc_result:
            # Transformer recommendation
            answer = f"""**Transformer Recommendation**

- **Speaker Load**: {calc_result.get('load_watts', '?')} W
- **Recommended Transformer**: {calc_result['recommended_watts']} W
- **Headroom**: {calc_result.get('headroom_percent', '?')}%

{calc_result.get('message', '')}"""
        
        else:
            answer = f"Calculation result: {calc_result}"
        
        return GeneratedAnswer(
            answer=answer,
            citations=[],
            confidence=1.0,  # Calculations are deterministic
            query_type="calculation",
            products_used=[],
        )
    
    
    def _format_products_for_llm(self, results: list[RetrievalResult]) -> str:
        """Format products for LLM prompt."""
        lines = []
        
        # Use same mappings as direct answer
        spec_mappings = [
            ('power_watts', 'Power', 'W', 'power_watts'),
            ('Power Handling (Long-term)', 'Power', 'W', 'power_watts'),
            ('freq_min_hz', 'Freq Min', 'Hz', 'freq_min_hz'),
            ('freq_max_hz', 'Freq Max', 'Hz', 'freq_max_hz'),
            ('Freq Response (-3 dB) Freq Range (-10 dB)', 'Freq Response', '', 'freq_response'),
            ('impedance_ohms', 'Impedance', 'Ω', 'impedance_ohms'),
            ('Nominal Impedance', 'Impedance', 'Ω', 'impedance_ohms'),
            ('sensitivity_db', 'Sensitivity', 'dB', 'sensitivity_db'),
            ('Sensitivity (SPL/1W@1m)', 'Sensitivity', 'dB', 'sensitivity_db'),
            ('coverage', 'Coverage', '', 'coverage'),
            ('Coverage (H × V, or Conical) 1 kHz - 4 kHz Average', 'Coverage', '', 'coverage'),
            ('voltage_type', 'Voltage', '', 'voltage_type'),
            ('driver_components', 'Drivers', '', 'driver_components'),
            ('Driver Components', 'Drivers', '', 'driver_components'),
            ('weight_kg', 'Weight', 'kg', 'weight_kg'),
            ('color_options', 'Colors', '', 'color_options'),
            ('environmental', 'Environmental', '', 'environmental'),
        ]
        
        for i, result in enumerate(results[:5], 1):  # Limit to top 5
            lines.append(f"\n### Product {i}: {result.model_name}")
            
            if result.category:
                lines.append(f"  Category: {result.category}")
            if result.series:
                lines.append(f"  Series: {result.series}")
            
            # Key specs using mappings
            specs = result.specs
            for key, label, unit, norm_key in spec_mappings:
                if key in specs and specs[key]:
                    val = specs[key]
                    suffix = f" {unit}" if unit else ""
                    lines.append(f"  {label}: {val}{suffix}")
            
            if result.ai_summary:
                lines.append(f"  Summary: {result.ai_summary}")
        
        return "\n".join(lines)
    
    def _fallback_answer(self, results: list[RetrievalResult]) -> GeneratedAnswer:
        """Generate fallback answer without LLM — format specs directly."""
        lines = []
        citations = []
        products_used = []
        
        for result in results[:5]:
            products_used.append(result.model_name)
            lines.append(f"\n**{result.model_name}**" + (f" ({result.category})" if result.category else ""))
            
            specs = result.specs
            spec_mappings = [
                ('power_watts', 'Power', 'W', 'power_watts'),
                ('Power Handling (Long-term)', 'Power', 'W', 'power_watts'),
                ('freq_min_hz', 'Freq Min', 'Hz', 'freq_min_hz'),
                ('freq_max_hz', 'Freq Max', 'Hz', 'freq_max_hz'),
                ('Freq Response (-3 dB) Freq Range (-10 dB)', 'Freq Response', '', 'freq_response'),
                ('impedance_ohms', 'Impedance', 'Ω', 'impedance_ohms'),
                ('Nominal Impedance', 'Impedance', 'Ω', 'impedance_ohms'),
                ('sensitivity_db', 'Sensitivity', 'dB', 'sensitivity_db'),
                ('Sensitivity (SPL/1W@1m)', 'Sensitivity', 'dB', 'sensitivity_db'),
                ('coverage', 'Coverage', '', 'coverage'),
                ('Coverage (H × V, or Conical) 1 kHz - 4 kHz Average', 'Coverage', '', 'coverage'),
                ('voltage_type', 'Voltage', '', 'voltage_type'),
                ('driver_components', 'Drivers', '', 'driver_components'),
                ('Driver Components', 'Drivers', '', 'driver_components'),
            ]
            
            for key, label, unit, norm_key in spec_mappings:
                if key in specs and specs[key] is not None:
                    value = specs[key]
                    suffix = f" {unit}" if unit else ""
                    lines.append(f"- {label}: {value}{suffix}")
                    citations.append(Citation(
                        model_name=result.model_name,
                        field=norm_key,
                        value=value,
                        pdf_source=result.pdf_source,
                    ))
            
            if result.ai_summary:
                lines.append(f"- Summary: {result.ai_summary}")
        
        answer_text = "\n".join(lines).strip()
        
        return GeneratedAnswer(
            answer=answer_text,
            citations=citations,
            confidence=0.7,
            query_type="semantic_search",
            products_used=products_used,
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
