import os
import json
from parser import load_guides
# This is the stable path for the new MCP SDK
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RedHatStyleAuditor")

current_dir = os.path.dirname(os.path.abspath(__file__))
GUIDES_DIR = os.path.join(current_dir, "guides")
HIDDEN_GUIDES_FILE = os.path.join(current_dir, ".hidden_guides.json")

def get_hidden_guides():
    """Load hidden guides list from file."""
    if os.path.exists(HIDDEN_GUIDES_FILE):
        try:
            with open(HIDDEN_GUIDES_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

@mcp.tool()
def search_style_guides(query: str) -> str:
    """Searches Red Hat style guides for a specific rule."""
    results = []
    if not os.path.exists(GUIDES_DIR):
        return "Error: /guides directory not found."

    # Load all guides using docling-enabled parser
    all_guides = load_guides(GUIDES_DIR)
    hidden_guides = get_hidden_guides()

    for guide_name, content in all_guides.items():
        # Skip hidden guides
        if any(guide_name in filename for filename in hidden_guides):
            continue

        if query.lower() in content.lower():
            results.append(f"--- From {guide_name} ---\n{content}")

    return "\n\n".join(results) if results else "No specific guideline found."

if __name__ == "__main__":
    mcp.run()
