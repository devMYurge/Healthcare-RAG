# rag_pipeline/ingest_images.py
import numpy as np
from PIL import Image
import chromadb

client = chromadb.PersistentClient(path="chroma_db")
image_collection = client.get_or_create_collection("image_docs")

def preprocess_image(path):
    img = Image.open(path).convert("RGB")
    return np.array(img)

def upsert_image(doc_id, image_path, metadata):
    arr = preprocess_image(image_path)
    emb = embed_images([arr])  # from embed.py
    image_collection.upsert(ids=[f"{doc_id}_img"], embeddings=emb, metadatas=[metadata], documents=[image_path])
