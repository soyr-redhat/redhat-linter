import os
import json
import hashlib
from parser import load_guides
from mcp.server.fastmcp import FastMCP
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

mcp = FastMCP("RedHatStyleAuditor")

current_dir = os.path.dirname(os.path.abspath(__file__))
GUIDES_DIR = os.path.join(current_dir, "guides")
HIDDEN_GUIDES_FILE = os.path.join(current_dir, ".hidden_guides.json")
VECTOR_DB_DIR = os.path.join(current_dir, ".vector_db")

# Initialize embeddings model (upgraded for better semantic search quality)
# all-mpnet-base-v2 is significantly better than all-MiniLM-L6-v2 for semantic similarity
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}  # Improves cosine similarity
)

# Global vector store
vector_store = None
last_guides_hash = None

def get_hidden_guides():
    """Load hidden guides list from file."""
    if os.path.exists(HIDDEN_GUIDES_FILE):
        try:
            with open(HIDDEN_GUIDES_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def get_guides_hash(guides_dict):
    """Generate hash of guides content to detect changes."""
    content = json.dumps(sorted(guides_dict.items()), sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()

def initialize_vector_store():
    """Initialize or update the vector store with chunked guide content."""
    global vector_store, last_guides_hash

    if not os.path.exists(GUIDES_DIR):
        return None

    # Load all guides
    all_guides = load_guides(GUIDES_DIR)
    hidden_guides = get_hidden_guides()

    # Filter out hidden guides
    active_guides = {
        name: content for name, content in all_guides.items()
        if not any(name in filename for filename in hidden_guides)
    }

    # Check if we need to rebuild
    current_hash = get_guides_hash(active_guides)
    if vector_store is not None and current_hash == last_guides_hash:
        return vector_store

    # Chunk the documents with improved settings for better retrieval
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,      # Increased from 500 to capture more context
        chunk_overlap=200,    # Increased from 50 to preserve continuity
        separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]  # Added heading separators
    )

    documents = []
    for guide_name, content in active_guides.items():
        chunks = text_splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            # Extract potential section header from chunk for better metadata
            lines = chunk.split('\n')
            section_header = ""
            for line in lines:
                if line.startswith('#'):
                    section_header = line.strip('#').strip()
                    break

            documents.append(Document(
                page_content=chunk,
                metadata={
                    "source": guide_name,
                    "chunk": i,
                    "section": section_header  # Add section context
                }
            ))

    if not documents:
        return None

    # Create new vector store
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=VECTOR_DB_DIR
    )

    last_guides_hash = current_hash
    return vector_store

@mcp.tool()
def search_style_guides(query: str, top_k: int = 5) -> str:
    """Intelligently searches W.I.P style guides using semantic search.

    Args:
        query: The search query (e.g., 'passive voice', 'acronyms')
        top_k: Number of most relevant chunks to return (default: 5, increased from 3)
    """
    import sys

    # Debug logging to stderr (will show in terminal)
    print(f"[MCP DEBUG] Tool called with query: '{query}', top_k={top_k}", file=sys.stderr)

    try:
        store = initialize_vector_store()
        if store is None:
            print("[MCP DEBUG] ERROR: Vector store is None", file=sys.stderr)
            return "Error: No style guides available."

        print(f"[MCP DEBUG] Vector store initialized successfully", file=sys.stderr)

        # Perform semantic search with more candidates to filter
        results = store.similarity_search_with_score(query, k=top_k * 2)

        if not results:
            print("[MCP DEBUG] No results found for query", file=sys.stderr)
            return "No specific guideline found."

        print(f"[MCP DEBUG] Found {len(results)} results", file=sys.stderr)

        # Filter and deduplicate results
        seen_content = set()
        formatted_results = []
        result_count = 0

        for idx, (doc, score) in enumerate(results):
            # Skip if we've seen very similar content
            content_hash = hash(doc.page_content[:200])
            if content_hash in seen_content:
                print(f"[MCP DEBUG] Skipping duplicate result {idx+1}", file=sys.stderr)
                continue
            seen_content.add(content_hash)

            # Skip results with very poor relevance (score > 1.5 is usually irrelevant for cosine)
            if score > 1.5:
                print(f"[MCP DEBUG] Skipping low-relevance result {idx+1} (score={score:.4f})", file=sys.stderr)
                continue

            source = doc.metadata.get('source', 'Unknown')
            section = doc.metadata.get('section', '')

            # Normalize score to percentage (lower score = better match)
            relevance = max(0, min(100, int((1.5 - score) / 1.5 * 100)))

            print(f"[MCP DEBUG] Result {idx+1}: {source} (score={score:.4f}, relevance={relevance}%)", file=sys.stderr)
            if section:
                print(f"[MCP DEBUG]   Section: {section}", file=sys.stderr)
            print(f"[MCP DEBUG]   Content preview: {doc.page_content[:150]}...", file=sys.stderr)

            # Include section header in output if available
            header = f"📚 {source}"
            if section:
                header += f" - {section}"
            header += f" (relevance: {relevance}%)"

            formatted_results.append(f"{header}\n{doc.page_content}")

            result_count += 1
            if result_count >= top_k:
                break

        if not formatted_results:
            return "No relevant guidelines found for this query."

        return "\n\n---\n\n".join(formatted_results)

    except Exception as e:
        print(f"[MCP DEBUG] Exception occurred: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return f"Search error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
