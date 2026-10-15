"""Minimal stdio MCP server standing in for the Gmail connector (tests only)."""
import sys
import time

try:  # mcp 2.x renamed FastMCP
    from mcp.server.mcpserver import MCPServer as FastMCP
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.exceptions import ToolError

mcp = FastMCP("fake-gmail")
MODE = sys.argv[1] if len(sys.argv) > 1 else "ok"


@mcp.tool()
def create_draft(to: str, subject: str, body: str) -> str:
    if MODE == "slow":
        time.sleep(30)
    if MODE == "auth":
        raise ToolError("401 Unauthorized: login required")
    return f'{{"id": "r-123", "link": "https://mail.example/#drafts/r-123", "to": "{to}"}}'


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:  # must never be called
    raise AssertionError("send was called")


if __name__ == "__main__":
    mcp.run()
