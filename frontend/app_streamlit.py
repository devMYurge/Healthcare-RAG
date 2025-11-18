# app_streamlit.py
import streamlit as st
from rag_pipeline.retriever import retrieve
from rag_pipeline.generator import generate_answer
# Initialize your LLM/VLM (omitted for brevity)

st.set_page_config(page_title="Healthcare RAG", layout="wide")

st.title("Healthcare Multimodal RAG")
st.caption("Informational use only. Not medical advice.")

query = st.text_input("Ask about a disease, diagnostic patterns, or report interpretation")
uploaded_image = st.file_uploader("Optional: upload a diagnostic image", type=["png","jpg","jpeg"])
uploaded_table = st.file_uploader("Optional: upload a CSV with lab values", type=["csv"])

if st.button("Search"):
    # Preprocess optional uploads and upsert to Chroma (or session-only collections)
    docs = retrieve(query, k=8)
    with st.spinner("Generating answer..."):
        answer = generate_answer(llm, query, docs)
    st.markdown("### Answer")
    st.write(answer)
    st.markdown("### Retrieved context")
    for i, d in enumerate(docs, 1):
        with st.expander(f"Source {i}: {d.metadata.get('title','')}"):
            st.write(d.page_content)
            st.code(d.metadata)
