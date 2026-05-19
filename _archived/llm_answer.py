import streamlit as st
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI
import os

# === Config ===
INDEX_ROOT = Path("data/faiss_index/")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OPENAI_MODEL = "gpt-4"
TOP_K = 5

# === UI Setup ===
st.set_page_config(page_title="🧠 GenAI Answer Assistant", page_icon="🤖", layout="centered")
st.title("🧠 GenAI Answer Assistant")
st.caption("Choose a document, ask a question, and get a natural language answer powered by LLM.")

# === Document Picker
index_dirs = sorted([d.name for d in INDEX_ROOT.iterdir() if d.is_dir()])
selected_doc = st.selectbox("📂 Select indexed document", index_dirs)

# === Question Input
question = st.text_input("💬 Ask your question", placeholder="e.g. What are the benefits of AWS public cloud?")
top_k = st.slider("🔢 Number of context chunks", min_value=1, max_value=10, value=TOP_K)

# === Answer Trigger
if selected_doc and question:
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db_path = INDEX_ROOT / selected_doc

    with st.spinner("🔍 Retrieving relevant chunks..."):
        db = FAISS.load_local(str(db_path), embeddings, allow_dangerous_deserialization=True)
        results = db.similarity_search(question, k=top_k)
        chunks = [doc.page_content for doc in results]
        context = "\n\n".join(chunks)

    with st.spinner("🤖 Generating LLM-powered answer..."):
        # Prevent older SDKs from receiving unsupported 'project' kwarg via env
        try:
            os.environ.pop("OPENAI_PROJECT", None)
        except Exception:
            pass
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = f"""
You are an intelligent assistant. Based on the following document excerpts, answer the user's question concisely and informatively.

Document Chunks:
{context}

Question:
{question}

Answer:"""
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()
        st.success("✅ Answer generated")

        st.markdown("### 🧠 Answer:")
        st.write(answer)

        with st.expander("📄 Show Retrieved Chunks"):
            for i, chunk in enumerate(chunks, 1):
                st.markdown(f"**Chunk {i}:**\n{chunk.strip()[:800]}...")

