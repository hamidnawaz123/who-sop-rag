import os
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()

SYSTEM_PROMPT = """
You are an expert WHO Standard Operating Procedures (SOP) Assistant.
STRICT RULE: Answer questions ONLY using the facts provided in the Context below. 
Do NOT use outside knowledge, speculate, or extrapolate.
If the answer cannot be found directly in the Context, respond strictly with: 
"I cannot answer this based on the provided SOP document."

LANGUAGE RULE:
The user may ask questions in Roman Urdu (e.g., "AFRO ka role kia hai?"). 
Understand the Roman Urdu query, extract facts strictly from the English Context, and answer clearly in English or Roman Urdu matching user preference while strictly maintaining context factual accuracy.
"""

_CACHED_MODEL = None

def get_working_model(client: Groq) -> str:
    """Live-tests models against Groq to find an active text model for your key."""
    global _CACHED_MODEL
    if _CACHED_MODEL:
        return _CACHED_MODEL

    available_models = [m.id for m in client.models.list().data]
    
    for model_id in available_models:
        # Skip audio, vision, guard, or specialized models
        if any(bad in model_id.lower() for bad in ["whisper", "vision", "guard", "orpheus", "safetensors"]):
            continue
        try:
            # Send a 1-token probe to confirm model accessibility
            client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            _CACHED_MODEL = model_id
            return _CACHED_MODEL
        except Exception:
            continue

    raise RuntimeError("No active, non-gated text completion models found for this Groq API key.")

def query_sop(user_query: str):
    model = SentenceTransformer("BAAI/bge-m3")
    query_vector = model.encode(user_query).tolist()
    
    client_db = chromadb.PersistentClient(path="./chroma_db")
    collection = client_db.get_or_create_collection(name="sop_chunks")
    
    
    results = collection.query(query_embeddings=[query_vector], n_results=3)
    raw_context = "\n\n".join(results["documents"][0])
    retrieved_context = raw_context[:3000]
    
 

# Pulls key from Streamlit Cloud Secrets first, then local .env
    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    groq_client = Groq(api_key=api_key)
    active_model = get_working_model(groq_client)
    
    response = groq_client.chat.completions.create(
        model=active_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{retrieved_context}\n\nQuestion: {user_query}"}
        ],
        temperature=0.0,
        max_tokens=1024
    )
    return response.choices[0].message.content