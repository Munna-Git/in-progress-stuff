"""
FastMCP Server for Bose Product Engine.
Exposes product query tools via Model Context Protocol.
"""

import asyncio
import logging
import sys
from typing import Optional

from src.config import settings
from src.server.tools import BoseProductTools

logger = logging.getLogger(__name__)


def create_server():
    """
    Create FastMCP server with Bose product tools.
    
    Returns:
        Configured MCP server instance
    """
    try:
        from fastmcp import FastMCP
    except ImportError:
        logger.error("fastmcp not installed. Install with: pip install fastmcp")
        raise
    
    # Initialize server
    mcp = FastMCP(
        name="bose-product-engine",
        description="Zero-hallucination product search for Bose professional audio equipment",
    )
    
    # Initialize tools
    tools = BoseProductTools()
    
    # Register query tool
    @mcp.tool()
    async def query_products(query: str) -> dict:
        """
        Query the Bose product database with natural language.
        
        Handles direct lookups, semantic search, and calculations.
        
        Args:
            query: Natural language query about Bose products
        """
        return await tools.query_products(query)
    
    # Register product lookup
    @mcp.tool()
    async def get_product(model_name: str) -> dict:
        """
        Get specifications for a specific Bose product.
        
        Args:
            model_name: Product model (e.g., "AM10/60", "DM3SE", "IZA 250-LZ")
        """
        result = await tools.get_product_specs(model_name)
        return result or {"error": f"Product '{model_name}' not found"}
    
    # Register search
    @mcp.tool()
    async def search_products(
        query: str,
        min_watts: Optional[int] = None,
        voltage_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list:
        """
        Search for Bose products with filters.
        
        Args:
            query: Search query
            min_watts: Minimum power requirement
            voltage_type: "70V", "100V", or "Low-Z"
            category: "loudspeaker", "amplifier", "controller"
            limit: Max results (default 10)
        """
        return await tools.search_products(
            query=query,
            min_watts=min_watts,
            voltage_type=voltage_type,
            category=category,
            limit=limit,
        )
    
    # Register similarity search
    @mcp.tool()
    async def find_similar(model_name: str, limit: int = 5) -> list:
        """
        Find products similar to a given model.
        
        Args:
            model_name: Reference product model
            limit: Max results (default 5)
        """
        return await tools.find_similar_products(model_name, limit)
    
    # Register 70V compatibility check
    @mcp.tool()
    def check_70v_compatibility(
        speaker_watts: list[int],
        transformer_watts: int,
    ) -> dict:
        """
        Check if speakers are compatible with a 70V transformer.
        
        Args:
            speaker_watts: List of speaker wattages
            transformer_watts: Transformer capacity
        """
        return tools.verify_70v_compatibility(speaker_watts, transformer_watts)
    
    # Register impedance calculator
    @mcp.tool()
    def calculate_impedance(
        impedances: list[float],
        connection: str,
    ) -> dict:
        """
        Calculate total impedance for series or parallel speakers.
        
        Args:
            impedances: List of impedances in ohms
            connection: "series" or "parallel"
        """
        return tools.calculate_impedance(impedances, connection)
    
    # Register transformer recommendation
    @mcp.tool()
    def recommend_transformer(total_watts: int) -> dict:
        """
        Recommend transformer size for speaker load.
        
        Args:
            total_watts: Total speaker wattage
        """
        return tools.recommend_transformer(total_watts)
    
    logger.info("FastMCP server created with Bose product tools")
    return mcp


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Run the MCP server.
    
    Args:
        host: Server host
        port: Server port
    """
    mcp = create_server()
    
    logger.info(f"Starting Bose Product Engine MCP server on {host}:{port}")
    
    # Run with uvicorn
    try:
        import uvicorn
        uvicorn.run(mcp.app, host=host, port=port)
    except ImportError:
        logger.error("uvicorn not installed. Install with: pip install uvicorn")
        raise


async def main():
    """Main entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Bose Product Engine MCP Server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)",
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
    
    # Run server
    run_server(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())
