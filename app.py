import streamlit as st
import os
import asyncio
import httpx
import sys
import json
from auditor_engine import RedHatAuditor

# --- 1. UI Configuration & Branding ---
st.set_page_config(
    page_title="W.I.P Editorial Auditor",
    layout="wide",
    initial_sidebar_state="collapsed"
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip('/')
HIDDEN_GUIDES_FILE = ".hidden_guides.json"

# Helper functions for persistent hidden guides
def save_hidden_guides(hidden_set):
    """Save hidden guides to file."""
    with open(HIDDEN_GUIDES_FILE, "w") as f:
        json.dump(list(hidden_set), f)

def load_hidden_guides():
    """Load hidden guides from file."""
    if os.path.exists(HIDDEN_GUIDES_FILE):
        try:
            with open(HIDDEN_GUIDES_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

# Custom CSS for minimalist, professional styling
st.markdown("""
    <style>
    /* Clean Diff Highlighting */
    .diff-box {
        padding: 16px;
        border-radius: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 0.95rem;
        min-height: 60px;
        border: 1px solid #d0d7de;
        line-height: 1.6;
    }
    .original-side {
        background-color: #fff5f5;
        color: #cf222e;
        border-left: 3px solid #cf222e;
    }
    .proposed-side {
        background-color: #f6fff8;
        color: #1a7f37;
        border-left: 3px solid #1a7f37;
    }
    .accepted-side {
        background-color: #ffffff;
        color: #24292e;
        border: 2px solid #1a7f37;
        position: relative;
    }
    .accepted-side::after {
        content: "ACCEPTED";
        position: absolute;
        top: 8px;
        right: 12px;
        font-size: 0.7rem;
        color: #1a7f37;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    /* Row container */
    .diff-row {
        margin-bottom: 16px;
    }

    /* Center Button Column */
    .merge-tools {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 12px;
    }

    /* Loading animation */
    .status-text {
        color: #cc0000;
        font-weight: 600;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }

    /* Clean page viewer */
    .page-container {
        background: white;
        border: 1px solid #d0d7de;
        border-radius: 6px;
        padding: 40px;
        min-height: 400px;
        max-height: 600px;
        overflow-y: auto;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        line-height: 1.7;
        color: #24292e;
    }

    .page-indicator {
        position: absolute;
        top: 12px;
        right: 16px;
        background: #f6f8fa;
        padding: 6px 14px;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #57606a;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Session State Initialization ---
# This prevents the AttributeError: st.session_state has no attribute "audit_results"
if 'audit_results' not in st.session_state:
    st.session_state.audit_results = None
if 'edits' not in st.session_state:
    st.session_state.edits = {}
if 'metrics' not in st.session_state:
    st.session_state.metrics = None
if 'show_document' not in st.session_state:
    st.session_state.show_document = False
if 'original_filename' not in st.session_state:
    st.session_state.original_filename = None
if 'confirm_clear_guides' not in st.session_state:
    st.session_state.confirm_clear_guides = False
if 'hidden_guides' not in st.session_state:
    st.session_state.hidden_guides = load_hidden_guides()

# --- 3. Sidebar: Settings & Knowledge Base ---
with st.sidebar:
    st.header("Settings")
    
    # Dynamic Model Selector
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1)
        models = [m['name'] for m in resp.json()['models']]
        # Set qwen2.5:3b as default if available
        default_index = 0
        if "qwen2.5:3b" in models:
            default_index = models.index("qwen2.5:3b")
        selected_model = st.selectbox("LLM Model", options=models, index=default_index)
    except:
        selected_model = "qwen2.5:3b"
        st.error("Ollama Offline")

    st.divider()
    
    # RAG Guide Manager
    st.subheader("Knowledge Base")
    if not os.path.exists("guides"):
        os.makedirs("guides")

    uploaded_guide = st.file_uploader(
        "Upload Style Guide",
        type=["md", "pdf", "docx", "html", "htm", "txt"],
        help="Supports: Markdown, PDF, DOCX, HTML, TXT"
    )
    if uploaded_guide:
        with open(os.path.join("guides", uploaded_guide.name), "wb") as f:
            f.write(uploaded_guide.getbuffer())
        st.rerun()

    st.caption("Active Guides:")
    supported_exts = ('.md', '.pdf', '.docx', '.html', '.htm', '.txt')
    for g in os.listdir("guides"):
        if g.lower().endswith(supported_exts):
            st.text(f"• {g}")

# --- 4. Main Application Header ---
st.title("WIPEA (W.I.P Editorial Auditor)")
st.markdown("Auditing for technical clarity and brand voice consistency.")

uploaded_file = st.file_uploader("Choose a .docx file", type="docx")

if uploaded_file:
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.button("Run Audit", type="primary", use_container_width=True):
        # UI Elements for dynamic loading updates
        status_placeholder = st.empty()
        
        # Function to update the UI while the agent works
        async def update_ui_status(text):
            status_placeholder.markdown(f"<p class='status-text'>{text}</p>", unsafe_allow_html=True)

        auditor = RedHatAuditor(model_name=selected_model, base_url=OLLAMA_BASE_URL)
        
        async def perform_audit():
            await auditor.initialize_tools()
            return await auditor.run_audit(temp_path, status_callback=update_ui_status)
        
        try:
            results = asyncio.run(perform_audit())
            st.session_state.audit_results = results
            st.session_state.metrics = auditor.calculate_metrics(results)
            st.session_state.edits = {} # Reset edits for new run
            st.session_state.show_document = False # Reset document viewer
            st.session_state.original_filename = uploaded_file.name # Store original filename
            status_placeholder.empty()
            st.rerun()
        except Exception as e:
            st.error(f"Audit failed: {e}")

# --- 5. Side-by-Side Interactive Review ---
if st.session_state.audit_results:
    st.divider()
    
    # Display Dashboard Metrics
    m = st.session_state.metrics
    m_cols = st.columns(5)
    for i, (label, val) in enumerate(m.items()):
        m_cols[i].metric(label, f"{val}%")

    st.divider()
    
    # Bulk Action Header
    st.subheader("Review")
    b1, b2, b3, _ = st.columns([1, 1, 1, 3])
    if b1.button("Accept All", type="primary"):
        for i in range(len(st.session_state.audit_results)): st.session_state.edits[i] = "accepted"
        st.rerun()
    if b2.button("Reject All"):
        for i in range(len(st.session_state.audit_results)): st.session_state.edits[i] = "rejected"
        st.rerun()
    if b3.button("Reset"):
        st.session_state.edits = {}; st.rerun()

    final_document = []

    # Table Header Labels
    st.markdown("<br>", unsafe_allow_html=True)
    h1, h2, h3 = st.columns([4, 1, 4])
    h1.caption("ORIGINAL CONTENT")
    h2.caption("ACTION")
    h3.caption("PROPOSED REWRITE")

    # The Editor Loop
    for idx, item in enumerate(st.session_state.audit_results):
        status = st.session_state.edits.get(idx, "pending")
        final_document.append(item['proposed_text'] if status == "accepted" else item['text'])

        # Static container for each diff row
        st.markdown("<div class='diff-row'>", unsafe_allow_html=True)
        row_orig, row_act, row_prop = st.columns([4, 1, 4])

        # Left Column: Original
        with row_orig:
            box_style = "original-side" if status != "rejected" else ""
            st.markdown(f"<div class='diff-box {box_style}'>{item['text']}</div>", unsafe_allow_html=True)
            if status == "pending":
                st.caption(f"Note: {item['feedback']}")

        # Middle Column: Decision Buttons
        with row_act:
            st.markdown("<div class='merge-tools'>", unsafe_allow_html=True)
            if status == "pending":
                if st.button("Accept", key=f"acc_{idx}", type="primary"):
                    st.session_state.edits[idx] = "accepted"
                    st.rerun()
                if st.button("Reject", key=f"rej_{idx}"):
                    st.session_state.edits[idx] = "rejected"
                    st.rerun()
            else:
                if st.button("Undo", key=f"undo_{idx}"):
                    st.session_state.edits[idx] = "pending"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Right Column: Proposed
        with row_prop:
            if status == "accepted":
                st.markdown(f"<div class='diff-box accepted-side'>{item['proposed_text']}</div>", unsafe_allow_html=True)
            elif status == "rejected":
                st.markdown("<div class='diff-box' style='opacity:0.3; background:#f0f0f0;'>Ignored</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='diff-box proposed-side'>{item['proposed_text']}</div>", unsafe_allow_html=True)
                if item['paper_trail']:
                    st.caption(f"Sources: {', '.join(item['paper_trail'])}")

        st.markdown("</div>", unsafe_allow_html=True)

    # Final Document Export
    st.divider()
    full_text = "\n\n".join(final_document)

    # View/Hide document button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Document" if not st.session_state.show_document else "Hide Document", use_container_width=True):
            st.session_state.show_document = not st.session_state.show_document
            st.rerun()

    # Generate download filename from original
    if st.session_state.original_filename:
        base_name = st.session_state.original_filename.rsplit('.', 1)[0]
        download_filename = f"{base_name}_revised.txt"
    else:
        download_filename = "audited_document_revised.txt"

    with col2:
        st.download_button("Download Audited Document", data=full_text, file_name=download_filename, type="primary", use_container_width=True)

    # Show full document if toggled
    if st.session_state.show_document:
        st.markdown("<div class='page-container'>{}</div>".format(full_text.replace('\n', '<br>')), unsafe_allow_html=True)

    # Local cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)

