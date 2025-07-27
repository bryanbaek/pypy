#!/usr/bin/env python3
"""
Run the MCP server for the business application.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backend.mcp.business_server import mcp


def main():
    """Main entry point for the MCP server."""
    try:
        print("Starting Business MCP Server...")
        print("Server name: business-mcp-server")
        print("Available tools: products, orders, appointments")
        print("Press Ctrl+C to stop the server")
        print("-" * 50)

        # Run the FastMCP server (this handles its own event loop)
        mcp.run()

    except KeyboardInterrupt:
        print("\n" + "-" * 50)
        print("Server stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
