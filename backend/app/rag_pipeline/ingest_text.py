# rag_pipeline/ingest_text.py
import chromadb
from chromadb.utils import embedding_functions
from rag_pipeline.embed import embed_text

client = chromadb.PersistentClient(path="chroma_db")
text_collection = client.get_or_create_collection("text_docs")

client = chromadb.CloudClient(
  api_key='ck-FnwMYBTt73NS22cSdp3TB6JhJLdgGH57AiiWwRXjp1Lw',
  tenant='34515262-ccb7-4a02-b878-670c7778a5c5',
  database='healthcare'
)

def upsert_text(doc_id, chunks, metadata):
    embeddings = embed_text(chunks)  # from embed.py
    ids = [f"{doc_id}_t_{i}" for i in range(len(chunks))]
    text_collection.upsert(ids=ids, embeddings=embeddings, metadatas=[metadata]*len(chunks), documents=chunks)
