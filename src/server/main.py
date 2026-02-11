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
        "bose-product-engine"
    )
    
    # Initialize tools
    tools = BoseProductTools()
    
    # Register ask tool
    @mcp.tool()
    async def ask(question: str) -> dict:
        """
        Ask a question about Bose products.
        
        Args:
            question: Natural language question about Bose products
        """
        return await tools.ask(question)
    
    # Register get_specs tool
    @mcp.tool()
    async def get_specs(model: str) -> dict:
        """
        Get specifications for a specific Bose product.
        
        Args:
            model: Product model (e.g., "AM10/60", "DM3SE")
        """
        result = await tools.get_specs(model)
        return result or {"error": f"Product '{model}' not found"}

    # Register get_models tool
    @mcp.tool()
    async def get_models() -> list:
        """
        Get a list of all available product models.
        """
        return await tools.get_models()

    # Register compare tool
    @mcp.tool()
    async def compare(models: list[str]) -> dict:
        """
        Compare specifications of multiple products side-by-side.
        
        Args:
            models: List of model names to compare
        """
        return await tools.compare(models)

    # Register sources tool
    @mcp.tool()
    async def sources() -> list:
        """
        Get list of available source documents.
        """
        return await tools.sources()

    # Register health tool
    @mcp.tool()
    async def health() -> dict:
        """
        Check system health.
        """
        return await tools.health()
    

    
    logger.info("FastMCP server created with Bose product tools")
    return mcp


async def run_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Run the MCP server.
    
    Args:
        host: Server host
        port: Server port
    """
    mcp = create_server()
    
    logger.info(f"Starting Bose Product Engine MCP server on {host}:{port}")
    
    # Run with FastMCP's built-in async runner
    await mcp.run_http_async(host=host, port=port, transport='sse')


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
    await run_server(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())
