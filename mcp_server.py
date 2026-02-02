import os
import glob
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("RedHatStyleAuditor")

GUIDES_DIR = "./guides"

@mcp.tool()
def search_style_guides(query: str) -> str:
    """
    Searches the Red Hat style guides for a specific rule or topic.
    """
    results = []
    # Ensure the directory exists so it doesn't crash
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
