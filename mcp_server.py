from mcp.server.fastmcp import FastMCP
import os
import glob

# Initialize FastMCP server
mcp = FastMCP("RedHatStyleAuditor")

GUIDES_DIR = "./guides"

@mcp.tool()
def search_style_guides(query: str) -> str:
    """
    Searches the Red Hat style guides for a specific rule or topic.
    Use this when you need to verify acronyms, filler words, or tone.
    """
    results = []
    # Search through all .md files in the guides directory
    for file_path in glob.glob(os.path.join(GUIDES_DIR, "*.md")):
        with open(file_path, "r") as f:
            content = f.read()
            # Simple keyword search for now; can be upgraded to semantic search
            if query.lower() in content.lower():
                results.append(f"--- From {os.path.basename(file_path)} ---\n{content}")
    
    if not results:
        return f"No specific Red Hat guideline found for '{query}'. Default to AP Style."
    
    return "\n\n".join(results)

@mcp.tool()
def list_all_guides() -> list:
    """Returns a list of all available Red Hat style guide categories."""
    return [f.replace(".md", "") for f in os.listdir(GUIDES_DIR) if f.endswith(".md")]

if __name__ == "__main__":
    mcp.run()
