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

# Initialize embeddings model (lightweight, runs locally)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
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

    # Chunk the documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    documents = []
    for guide_name, content in active_guides.items():
        chunks = text_splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk,
                metadata={"source": guide_name, "chunk": i}
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
def search_style_guides(query: str, top_k: int = 3) -> str:
    """Intelligently searches W.I.P style guides using semantic search.

    Args:
        query: The search query (e.g., 'passive voice', 'acronyms')
        top_k: Number of most relevant chunks to return (default: 3)
    """
    try:
        store = initialize_vector_store()
        if store is None:
            return "Error: No style guides available."

        # Perform semantic search
        results = store.similarity_search_with_score(query, k=top_k)

        if not results:
            return "No specific guideline found."

        # Format results with relevance scores
        formatted_results = []
        for doc, score in results:
            source = doc.metadata.get('source', 'Unknown')
            # Lower score = more relevant in some systems, normalize to percentage
            relevance = max(0, min(100, int((1 - score) * 100)))
            formatted_results.append(
                f"📚 {source} (relevance: {relevance}%)\n{doc.page_content}"
            )

        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"Search error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
