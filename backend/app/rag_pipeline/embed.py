# rag_pipeline/embed.py
from sentence_transformers import SentenceTransformer
import torch

TEXT_EMB_MODEL = "BAAI/bge-m3"  # good multi-lingual, multi-vector-friendly
IMG_EMB_MODEL = "openai/clip-vit-large-patch14"  # via sentence-transformers or transformers

text_model = SentenceTransformer(TEXT_EMB_MODEL, device="cpu")
img_model = SentenceTransformer(IMG_EMB_MODEL, device="cpu")

def embed_text(chunks: list[str]):
    return text_model.encode(chunks, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)

def embed_images(img_arrays):
    return img_model.encode(img_arrays, batch_size=8, convert_to_numpy=True, normalize_embeddings=True)