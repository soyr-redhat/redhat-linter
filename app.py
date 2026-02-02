import streamlit as st
import os
import asyncio
import httpx
from auditor_engine import RedHatAuditor

# --- 1. UI Configuration & Branding ---
st.set_page_config(page_title="Red Hat Linter", page_icon="🎩", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for UI polish
st.markdown("""
    <style>
    .diff-removed { background-color: #ffeef0; text-decoration: line-through; color: #b31d28; padding: 2px; border-radius: 3px; }
    .diff-added { background-color: #e6ffed; color: #22863a; padding: 2px; font-weight: bold; border-radius: 3px; }
    .editor-card { border-left: 5px solid #e0e0e0; padding: 15px; margin-bottom: 20px; background-color: #ffffff; border-radius: 0 5px 5px 0; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .editor-card-accepted { border-left: 5px solid #28a745; background-color: #f8fff9; padding: 15px; margin-bottom: 20px; border-radius: 0 5px 5px 0; }
    .editor-card-rejected { border-left: 5px solid #dc3545; background-color: #fff8f8; padding: 15px; margin-bottom: 20px; border-radius: 0 5px 5px 0; opacity: 0.8; }
    .bulk-action-bar { padding: 15px; background-color: #f1f3f4; border-radius: 8px; margin-bottom: 20px; border: 1px solid #d1d3d4; }
    .status-text { color: #555; font-style: italic; animation: fadeInOut 2s infinite; }
    @keyframes fadeInOut { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. State Management ---
if 'audit_results' not in st.session_state: st.session_state.audit_results = None
if 'edits' not in st.session_state: st.session_state.edits = {} 
if 'metrics' not in st.session_state: st.session_state.metrics = None

# --- 3. Sidebar Configuration ---
with st.sidebar:
    st.title("⚙️ Auditor Settings")
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=1)
        models = [m['name'] for m in resp.json()['models']]
        selected_model = st.selectbox("Current LLM", options=models, index=0)
    except:
        selected_model = "llama3.1"; st.error("Ollama Offline")
    
    st.divider()
    if not os.path.exists("guides"): os.makedirs("guides")
    uploaded_guide = st.file_uploader("Upload .md Rules", type="md")
    if uploaded_guide:
        with open(os.path.join("guides", uploaded_guide.name), "wb") as f: f.write(uploaded_guide.getbuffer())
        st.rerun()
    for g in os.listdir("guides"): 
        if g.endswith(".md"): st.markdown(f"📖 `{g}`")

# --- 4. Main Interface ---
st.title("🎩 Red Hat Editorial Auditor")

uploaded_file = st.file_uploader("Upload Document for Audit", type="docx")

if uploaded_file:
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())

    if st.button("🚀 Analyze Content", type="primary", use_container_width=True):
        # UI Elements for the status updates
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        # Callback to update the UI from the engine
        async def update_status(text):
            status_placeholder.markdown(f"<p class='status-text'>{text}</p>", unsafe_allow_html=True)

        auditor = RedHatAuditor(model_name=selected_model)
        
        async def run_flow():
            await auditor.initialize_tools()
            return await auditor.run_audit(temp_path, status_callback=update_status)
        
        with st.spinner("Agent is consulting style guides..."):
            try:
                results = asyncio.run(run_flow())
                st.session_state.audit_results = results
                st.session_state.metrics = auditor.calculate_metrics(results)
                st.session_state.edits = {} 
                st.rerun()
            except Exception as e:
                st.error(f"Audit Error: {e}")

# --- 5. Interactive Editor Section ---
if st.session_state.audit_results:
    st.divider()
    
    # 5a. Metrics
    m = st.session_state.metrics
    cols = st.columns(5)
    for i, (label, val) in enumerate(m.items()): cols[i].metric(label, f"{val}%")

    st.divider()
    
    # 5b. BULK ACTION BAR
    st.subheader("🖋️ Interactive Review")
    st.markdown("<div class='bulk-action-bar'>", unsafe_allow_html=True)
    b1, b2, b3, _ = st.columns([1, 1, 1, 3])
    if b1.button("✅ Accept All"):
        for i in range(len(st.session_state.audit_results)): st.session_state.edits[i] = "accepted"
        st.rerun()
    if b2.button("❌ Reject All"):
        for i in range(len(st.session_state.audit_results)): st.session_state.edits[i] = "rejected"
        st.rerun()
    if b3.button("🔄 Reset"):
        st.session_state.edits = {}; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    final_doc_list = []

    # 5c. The Editor Row
    for idx, item in enumerate(st.session_state.audit_results):
        status = st.session_state.edits.get(idx, "pending")
        
        if status == "accepted":
            final_doc_list.append(item['proposed_text'])
            card_class, diff = "editor-card-accepted", f"<span class='diff-added'>{item['proposed_text']}</span>"
        elif status == "rejected":
            final_doc_list.append(item['text'])
            card_class, diff = "editor-card-rejected", item['text']
        else:
            final_doc_list.append(item['text'])
            card_class = "editor-card"
            diff = f"<span class='diff-removed'>{item['text']}</span> <span class='diff-added'>{item['proposed_text']}</span>"

        st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
        c_main, c_btns = st.columns([4, 1])
        with c_main:
            st.markdown(diff, unsafe_allow_html=True)
            if status == "pending":
                st.caption(f"💡 **Feedback:** {item['feedback']}")
                if item['paper_trail']: st.caption(f"🔍 *Sources: {', '.join(item['paper_trail'])}*")
        with c_btns:
            if status == "pending":
                if st.button("Accept", key=f"a{idx}"): st.session_state.edits[idx] = "accepted"; st.rerun()
                if st.button("Ignore", key=f"r{idx}"): st.session_state.edits[idx] = "rejected"; st.rerun()
            else:
                if st.button("Undo", key=f"u{idx}"): st.session_state.edits[idx] = "pending"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 5d. Export
    st.divider()
    full_text = "\n\n".join(final_doc_list)
    st.text_area("Final Preview", value=full_text, height=300)
    st.download_button("📥 Download Text", data=full_text, file_name="audited_doc.txt")

    if os.path.exists(temp_path): os.remove(temp_path)
