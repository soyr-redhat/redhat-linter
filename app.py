import streamlit as st
import os
import json
from parser import RedHatParser, load_guides

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
    # 1. Parse Document
    # We save temporarily to allow the parser to read it
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    parser = RedHatParser(temp_path)
    structured_content = parser.get_structured_content()

    # 2. Metrics Header (The 5 Cs)
    st.subheader("Performance Metrics")
    m1, m2, m3, m4, m5 = st.columns(5)
    
    # Mock scores (In the next step, these will be calculated by auditor_engine.py)
    m1.metric("Clear", "82%", "Helpful")
    m2.metric("Concise", "65%", "-5%", delta_color="inverse")
    m3.metric("Conversational", "91%", "Authentic")
    m4.metric("Credible", "78%", "Needs Citations")
    m5.metric("Compelling", "88%", "Brave")

    st.divider()

    # 3. Side-by-Side Audit View
    col_orig, col_audit = st.columns([1, 1])

    with col_orig:
        st.subheader("Original Content")
        for item in structured_content:
            if item['type'] == "heading":
                st.markdown(f"### {item['text']}")
            elif item['type'] == "list_item":
                st.markdown(f"* {item['text']}")
            else:
                st.write(item['text'])

    with col_audit:
        st.subheader("Audit & Suggestions")
        
        # This is where the Auditor Engine would output its specific flags
        # For now, we show a sample of how the agent's feedback will look
        for item in structured_content:
            # Placeholder for AI Logic: 
            # In your real loop, you'd call auditor_engine.audit(item['text'])
            if "In order to" in item['text']:
                st.warning(f"**Brevity Violation:** Replace 'In order to' with 'To'.")
            
            if item['type'] == "heading" and any(word[0].isupper() for word in item['text'].split()[1:]):
                 st.error(f"**Formatting:** Use sentence case for headlines.")

            # Add a spacer to keep columns somewhat aligned
            st.write("") 

    # Cleanup
    os.remove(temp_path)

else:
    st.warning("Please upload a .docx file to begin.")
