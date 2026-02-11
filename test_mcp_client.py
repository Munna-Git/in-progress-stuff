"""
Test script for Bose Product Engine MCP Server.
Connects to the local MCP server and tests the tools.

Usage:
    python test_mcp_client.py
"""

import asyncio
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def main():
    # We will use the mcp python client to connect
    # First, we need to make sure the server IS RUNNING in another terminal
    # python -m src.server.main
    
    print("="*60)
    print("MCP CLIENT TEST")
    print("="*60)
    print("Connecting to http://localhost:8002/sse ...")
    
    try:
        from mcp.client.sse import sse_client
        from mcp import ClientSession, StdioServerParameters
    except ImportError:
        print("Please install mcp: pip install mcp")
        return

    # Connect via SSE
    try:
        async with sse_client("http://localhost:8002/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # List tools
                print("\n--- Available Tools ---")
                tools = await session.list_tools()
                for tool in tools.tools:
                    print(f"- {tool.name}: {tool.description}")
                
                # Test 1: get_models
                print("\n--- Testing: get_models ---")
                models = await session.call_tool("get_models", {})
                model_list = models.content[0].text
                print(f"Models found: {len(eval(model_list))} (showing first 5)")
                print(eval(model_list)[:5])
                
                # Test 2: get_specs
                model = "DesignMax.DM3C"
                print(f"\n--- Testing: get_specs('{model}') ---")
                specs = await session.call_tool("get_specs", {"model": model})
                print(specs.content[0].text[:500] + "...")
                
                # Test 3: ask (Direct)
                question = "What is the power of the DM3C?"
                print(f"\n--- Testing: ask('{question}') ---")
                answer = await session.call_tool("ask", {"question": question})
                print(answer.content[0].text)
                
                # Test 4: compare
                print("\n--- Testing: compare ---")
                comparison = await session.call_tool("compare", {"models": ["DesignMax.DM3C", "DesignMax.DM5C"]})
                print(comparison.content[0].text)

                # Test 5: health
                print("\n--- Testing: health ---")
                health = await session.call_tool("health", {})
                print(health.content[0].text)

    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure the server is running: python -m src.server.main")

if __name__ == "__main__":
    asyncio.run(main())
