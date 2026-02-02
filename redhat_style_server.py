import os
import glob
# This is the stable path for the new MCP SDK
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RedHatStyleAuditor")

current_dir = os.path.dirname(os.path.abspath(__file__))
GUIDES_DIR = os.path.join(current_dir, "guides")

@mcp.tool()
def search_style_guides(query: str) -> str:
    """Searches Red Hat style guides for a specific rule."""
    results = []
    if not os.path.exists(GUIDES_DIR):
        return "Error: /guides directory not found."

    for file_path in glob.glob(os.path.join(GUIDES_DIR, "*.md")):
        with open(file_path, "r") as f:
            content = f.read()
            if query.lower() in content.lower():
                results.append(f"--- From {os.path.basename(file_path)} ---\n{content}")
    
    return "\n\n".join(results) if results else "No specific guideline found."

if __name__ == "__main__":
    mcp.run()
