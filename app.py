import streamlit as st
import os
import asyncio
import httpx
import sys
from auditor_engine import RedHatAuditor

# --- 1. UI Configuration & Branding ---
st.set_page_config(
    page_title="Red Hat Editorial Auditor",
    page_icon="🎩",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for the Side-by-Side Editor and Status Animations
st.markdown("""
    <style>
    /* GitHub-style Diff Highlighting */
    .diff-box {
        padding: 12px;
        border-radius: 6px;
        font-family: 'Source Code Pro', monospace;
        font-size: 0.95rem;
        min-height: 100px;
        border: 1px solid #e1e4e8;
        line-height: 1.5;
    }
    .original-side { background-color: #ffeef0; color: #b31d28; text-decoration: line-through; }
    .proposed-side { background-color: #e6ffed; color: #22863a; font-weight: 500; }
    .accepted-side { background-color: #ffffff; color: #24292e; border: 2px solid #28a745; position: relative; }
    .accepted-side::after { content: "✅ ACCEPTED"; position: absolute; top: 5px; right: 10px; font-size: 0.7rem; color: #28a745; font-weight: bold; }
    
    /* Center Button Column Styling */
    .merge-tools {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 10px;
    }

    /* Pulse animation for the loading status */
    .status-text { color: #cc0000; font-weight: bold; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
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

# --- 3. Sidebar: Settings & Knowledge Base ---
with st.sidebar:
    st.header("Settings")
    
    # Dynamic Model Selector
    try:
        OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1)
        models = [m['name'] for m in resp.json()['models']]
        selected_model = st.selectbox("LLM Model", options=models, index=0)
    except:
        selected_model = "llama3.1"
        st.error("Ollama Offline")

    st.divider()
    
    # RAG Guide Manager
    st.subheader("Knowledge Base")
    if not os.path.exists("guides"):
        os.makedirs("guides")
    
    uploaded_guide = st.file_uploader("Upload Style Guide (.md)", type="md")
    if uploaded_guide:
        with open(os.path.join("guides", uploaded_guide.name), "wb") as f:
            f.write(uploaded_guide.getbuffer())
        st.rerun()
    
    st.caption("Active Guides:")
    for g in os.listdir("guides"):
        if g.endswith(".md"):
            st.text(f"📖 {g}")

# --- 4. Main Application Header ---
st.title("RHEA (Red Hat Editorial Auditor)")
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

        auditor = RedHatAuditor(model_name=selected_model)
        
        async def perform_audit():
            await auditor.initialize_tools()
            return await auditor.run_audit(temp_path, status_callback=update_ui_status)
        
        try:
            results = asyncio.run(perform_audit())
            st.session_state.audit_results = results
            st.session_state.metrics = auditor.calculate_metrics(results)
            st.session_state.edits = {} # Reset edits for new run
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
    if b1.button("✅ Accept All"):
        for i in range(len(st.session_state.audit_results)): st.session_state.edits[i] = "accepted"
        st.rerun()
    if b2.button("❌ Reject All"):
        for i in range(len(st.session_state.audit_results)): st.session_state.edits[i] = "rejected"
        st.rerun()
    if b3.button("🔄 Reset"):
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

        row_orig, row_act, row_prop = st.columns([4, 1, 4])

        # Left Column: Original
        with row_orig:
            box_style = "original-side" if status != "rejected" else ""
            st.markdown(f"<div class='diff-box {box_style}'>{item['text']}</div>", unsafe_allow_html=True)
            if status == "pending":
                st.caption(f"💡 {item['feedback']}")

        # Middle Column: Decision Buttons
        with row_act:
            st.markdown("<div class='merge-tools'>", unsafe_allow_html=True)
            if status == "pending":
                if st.button("➡️", key=f"acc_{idx}", help="Accept Rewrite"):
                    st.session_state.edits[idx] = "accepted"
                    st.rerun()
                if st.button("✖️", key=f"rej_{idx}", help="Keep Original"):
                    st.session_state.edits[idx] = "rejected"
                    st.rerun()
            else:
                if st.button("↩️", key=f"undo_{idx}"):
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

    # Final Document Preview and Export
    st.divider()
    st.subheader("Final Preview")
    full_text = "\n\n".join(final_document)
    st.text_area("Corrected Text", value=full_text, height=300)
    st.download_button("Download Result", data=full_text, file_name="audited_redhat_content.txt")

    # Local cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)

