import os
import subprocess
import streamlit as st

# 1. MUST BE THE VERY FIRST STREAMLIT COMMAND
st.set_page_config(layout="wide", page_title="WHO SOP Assistant")

# Lazy import query_sop to ensure DB exists before query_engine initializes
from query_engine import query_sop

# 2. Auto-ingest SOP PDF if database directory is missing or empty
import os
import subprocess
import streamlit as st
import chromadb

st.set_page_config(layout="wide", page_title="WHO SOP Assistant")

@st.cache_resource
def setup_database():
    # Check directly inside ChromaDB if the collection exists and has chunks
    needs_ingestion = True
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="sop_chunks")
        if collection.count() > 0:
            needs_ingestion = False
    except Exception:
        needs_ingestion = True

    if needs_ingestion:
        st.warning("First-time setup: Building ChromaDB vector store from SOP document...")
        result = subprocess.run(["python", "ingest.py"], capture_output=True, text=True)
        
        if result.returncode != 0:
            st.error("Ingestion failed during startup.")
            st.code(result.stderr)
            st.stop()
            
        st.success("Vector store successfully built!")

setup_database()

# Lazy-import query_engine AFTER database ingestion completes
from query_engine import query_sop

SOP_SECTIONS = {
    "Section 1: Introduction": "Defines acute public health events (PHEs) in AFR (over 85% being infectious disease outbreaks) and the roles of COs, AFRO, IST, and HQ.",
    "Section 2: Purpose & Scope": "Sets standard operations based on timeliness, consistency, technical excellence, and accountability across all WHO operational levels.",
    "Section 3: Rationale": "Describes early warning coordination to prevent disease transmission across all 46 AFR member states despite limited country capacity.",
    "Section 4: Operational Readiness": "Outlines readiness functions, APHEF funding mechanisms, RRT rosters, stockpiles, and emergency procurement procedures.",
    "Section 5: Detecting & Assessing Acute PHEs": "Details media triage within 24h, Rapid Risk Assessment (RRA) criteria, EMS entry, and convening AFRO Emergency Meetings.",
    "Section 6: Activating PHE Response": "Covers deployment of experts (24–72h for staff, 3–5 days for consultants), APHEF fund authorization, and logistics shipment within 72h.",
    "Section 7: PHE Communications": "Defines operational communications (Sitreps, EMS), risk communications (EIS updates within 6–12h, Outbreak News), and media talking points.",
    "Section 8: Monitoring PHE Response": "Establishes the continual risk management cycle (detection, risk assessment, control, evaluation) and regular joint teleconferences.",
    "Section 9: Evaluation of PHE Response": "Mandates formative/summative evaluations within 4 weeks after an outbreak is declared over to assess response effectiveness.",
    "Section 10: Improve Preparedness & Planning": "Guidelines for updating country and regional preparedness plans within 3 months based on post-response evaluation lessons.",
    "Section 11: Response at WHO Country Office": "Specific CO workflows: verifying alerts within 24h, activating Task Forces, issuing preliminary reports within 48h, and daily Sitreps."
}

st.title("WHO Regional Office for Africa — SOP Chatbot")

col_chat, col_summary = st.columns([2, 1])

with col_chat:
    st.subheader("Chatbot (Supports English & Roman Urdu)")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask a question (e.g., 'Verification process kitna time leta hai?')..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("Searching SOPs..."):
                response = query_sop(user_input)
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

with col_summary:
    st.subheader("SOP Document Structure")
    st.caption("Click any section to expand its summary")
    
    for sec_title, sec_summary in SOP_SECTIONS.items():
        with st.expander(sec_title):
            st.write(sec_summary)