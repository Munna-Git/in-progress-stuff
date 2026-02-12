"""
Ollama Synthesizer for generating product summaries.
Uses local Ollama LLM for zero-hallucination summarization.
"""

import asyncio
import logging
from typing import Any, Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class OllamaSynthesizer:
    """
    Generate AI summaries for products using local Ollama LLM.
    
    Uses llama3.2:3b for fast, local summarization that enhances
    semantic search without hallucinating specifications.
    """
    
    SUMMARIZATION_PROMPT = """You are a technical writer summarizing Bose professional audio equipment.
Given the following product specifications, write a concise 2-3 sentence summary.
Focus on: what the product is, its key use cases, and standout features.
Do NOT make up any specifications that aren't provided.
Do NOT include marketing fluff.
Be factual and technical.

Product: {model_name}
Category: {category}
Series: {series}

Specifications:
{specs_text}

Summary:"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """Initialize the Ollama synthesizer."""
        self.base_url = (base_url or settings.ollama_base_url).rstrip('/')
        self.model = model or settings.ollama_llm_model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> bool:
        """Check if Ollama is available and model is loaded."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            
            if response.status_code != 200:
                logger.error(f"Ollama health check failed: {response.status_code}")
                return False
            
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            
            # Check if our model is available (with or without version tag)
            model_base = self.model.split(':')[0]
            model_available = any(
                model_base in m for m in models
            )
            
            if not model_available:
                logger.warning(
                    f"Model {self.model} not found. Available: {models}. "
                    f"Run: ollama pull {self.model}"
                )
                return False
            
            logger.info(f"Ollama health check passed. Model: {self.model}")
            return True
            
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def generate_summary(
        self,
        model_name: str,
        category: str,
        series: str,
        specs: dict[str, Any],
    ) -> Optional[str]:
        """
        Generate a summary for a product.
        
        Args:
            model_name: Product model name
            category: Product category
            series: Product series
            specs: Product specifications dict
            
        Returns:
            Generated summary text, or None on failure
        """
        # Format specs for prompt
        specs_text = self._format_specs(specs)
        
        prompt = self.SUMMARIZATION_PROMPT.format(
            model_name=model_name,
            category=category,
            series=series,
            specs_text=specs_text,
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
                        "temperature": 0.3,  # Lower temperature for factual output
                        "num_predict": 150,  # Limit response length
                    },
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama generate failed: {response.status_code}")
                return None
            
            data = response.json()
            summary = data.get('response', '').strip()
            
            # Clean up the summary
            summary = self._clean_summary(summary)
            
            logger.debug(f"Generated summary for {model_name}: {summary[:50]}...")
            return summary
            
        except httpx.TimeoutException:
            logger.warning(f"Timeout generating summary for {model_name}")
            return None
        except Exception as e:
            logger.error(f"Error generating summary for {model_name}: {e}")
            return None
    
    def _format_specs(self, specs: dict[str, Any]) -> str:
        """Format specifications for the prompt."""
        lines = []
        
        # Priority specs to include
        priority_keys = [
            ('power_watts', 'Power', 'W'),
            ('freq_min_hz', 'Frequency Min', 'Hz'),
            ('freq_max_hz', 'Frequency Max', 'Hz'),
            ('impedance_ohms', 'Impedance', 'ohms'),
            ('sensitivity_db', 'Sensitivity', 'dB'),
            ('coverage', 'Coverage', ''),
            ('driver_components', 'Drivers', ''),
            ('voltage_type', 'Voltage Type', ''),
            ('environmental', 'Environmental', ''),
            ('color_options', 'Colors', ''),
        ]
        
        for key, label, unit in priority_keys:
            value = specs.get(key)
            if value:
                if unit:
                    lines.append(f"- {label}: {value} {unit}")
                else:
                    lines.append(f"- {label}: {value}")
        
        return '\n'.join(lines) if lines else 'No specifications available'
    
    def _clean_summary(self, summary: str) -> str:
        """Clean and validate the generated summary."""
        # Remove any leading/trailing quotes
        summary = summary.strip('"\'')
        
        # Remove "Summary:" prefix if present
        if summary.lower().startswith('summary:'):
            summary = summary[8:].strip()
        
        # Limit to reasonable length
        if len(summary) > 500:
            # Find last complete sentence
            sentences = summary[:500].split('.')
            if len(sentences) > 1:
                summary = '.'.join(sentences[:-1]) + '.'
            else:
                summary = summary[:500] + '...'
        
        return summary
    
    async def synthesize_batch(
        self,
        products: list[dict],
        concurrency: int = 1,
    ) -> list[dict]:
        """
        Generate summaries for a batch of products.
        
        Args:
            products: List of product dicts with model_name, category, series, specs
            concurrency: Max concurrent requests
            
        Returns:
            List of products with ai_summary added
        """
        logger.info(f"Synthesizing summaries for {len(products)} products")
        
        # Check Ollama availability
        if not await self.health_check():
            logger.warning("Ollama not available, skipping synthesis")
            return products
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_product(product: dict) -> dict:
            async with semaphore:
                summary = await self.generate_summary(
                    model_name=product.get('model_name', ''),
                    category=product.get('category', ''),
                    series=product.get('series', ''),
                    specs=product.get('specs', {}),
                )
                
                result = product.copy()
                result['ai_summary'] = summary
                return result
        
        tasks = [process_product(p) for p in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing product {i}: {result}")
                product = products[i].copy()
                product['ai_summary'] = None
                final_results.append(product)
            else:
                final_results.append(result)
        
        success_count = sum(1 for r in final_results if r.get('ai_summary'))
        logger.info(f"Generated {success_count}/{len(products)} summaries")
        
        return final_results
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
