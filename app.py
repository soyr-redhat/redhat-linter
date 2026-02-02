import streamlit as st
import os
import json
from parser import RedHatParser, load_guides
from auditor_engine import RedHatAuditor

# --- Page Configuration ---
st.set_page_config(
    page_title="Red Hat Style Auditor",
    page_icon="🎩",
    layout="wide"
)

# Custom CSS for that "Red Hat" feel
st.markdown("""
    <style>
    .metric-card { border: 1px solid #e6e6e6; padding: 10px; border-radius: 5px; }
    .stAlert { padding: 0.5rem; margin-bottom: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar: Dashboard & Guides ---
with st.sidebar:
    st.title("Auditor Control")
    st.divider()
    
    # Load and show available guides
    guides = load_guides()
    if "error" not in guides:
        st.subheader("Loaded Style Guides")
        for guide in guides.keys():
            st.caption(f"{guide.replace('_', ' ').title()}")
    else:
        st.error("No guides found in /guides directory!")

    st.divider()
    st.info("Ensure your MCP server is running in the background for live rule lookups.")

# --- Main UI ---
st.title("Red Hat Blog & Paper Auditor")
st.write("Drag in your .docx draft to analyze it against the Red Hat Corporate Style Guide.")

uploaded_file = st.file_uploader("Upload Document", type=["docx"])

if uploaded_file:
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Initialize Parser
    parser = RedHatParser(temp_path)
    structured_content = parser.get_structured_content()

    # Create a "Run Audit" Button
    if st.button("🚀 Run Red Hat Style Audit"):
        with st.spinner("Agent is consulting style guides..."):
            auditor = RedHatAuditor()
            # Store results in session state so they persist
            st.session_state['audit_results'] = auditor.run_audit(temp_path)
    
    st.divider()

    # 3. Side-by-Side Audit View
    col_orig, col_audit = st.columns([1, 1])

    with col_orig:
        st.subheader("Original Content")
        for item in structured_content:
            if item['type'] == "heading":
                st.markdown(f"### {item['text']}")
            else:
                st.write(item['text'])

    with col_audit:
        st.subheader("Agent Critique")
        if 'audit_results' in st.session_state:
            for result in st.session_state['audit_results']:
                # Display the AI feedback in a nice card
                with st.expander(f"Analysis: {result['text'][:40]}...", expanded=True):
                    st.write(result['feedback'])
        else:
            st.info("Click 'Run Red Hat Style Audit' to see feedback.")

    os.remove(temp_path)
