"""
Unified ingestion and embedding utilities for Healthcare-RAG

This single module replaces the multiple smaller scripts under
`rag_pipeline/` (ingest_text, ingest_pdf, ingest_tables, ingest_images,
embed) and provides reusable functions to:
 - initialize a Chroma client and collections
 - embed text and images via sentence-transformers
 - ingest text chunks, CSV tables, PDFs and images into Chroma

Usage: import functions from this module or run as a script to ingest
the two sample PDFs (if present).
"""
from __future__ import annotations

import os
import glob
import hashlib
from typing import List, Dict, Optional

try:
    import numpy as np
except Exception:
    np = None

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

import chromadb
from chromadb.config import Settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import torch
except Exception:
    torch = None


DEFAULT_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", os.path.join(os.getcwd(), "backend", "data", "chroma"))
DEFAULT_TEXT_EMB = os.getenv("TEXT_EMB_MODEL", "BAAI/bge-m3")
DEFAULT_IMG_EMB = os.getenv("IMG_EMB_MODEL", "openai/clip-vit-large-patch14")


def _make_client(persist_dir: str = DEFAULT_PERSIST_DIR):
    """Create a chroma client using a persist directory."""
    try:
        settings = Settings(persist_directory=persist_dir)
        client = chromadb.Client(settings)
        return client
    except Exception as e:
        # As a fallback, try the older PersistentClient if available
        try:
            client = chromadb.PersistentClient(path=persist_dir)
            return client
        except Exception:
            raise RuntimeError(f"Failed to initialize Chroma client: {e}")


class Ingestor:
    def __init__(self, persist_dir: str = DEFAULT_PERSIST_DIR, text_model: str = DEFAULT_TEXT_EMB, img_model: str = DEFAULT_IMG_EMB, device: Optional[str] = None):
        self.client = _make_client(persist_dir)
        # Collections
        self.text_collection = self._get_or_create_collection("text_docs")
        self.table_collection = self._get_or_create_collection("table_docs")
        self.image_collection = self._get_or_create_collection("image_docs")

        # Device auto-detection
        if device is None:
            if torch is not None and torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"

        # Load embedding models if available
        if SentenceTransformer is None:
            self.text_model = None
            self.img_model = None
            print("sentence-transformers not installed; embedding functions will raise if used.")
        else:
            try:
                self.text_model = SentenceTransformer(text_model, device=device)
            except Exception as e:
                print(f"Failed to load text embedding model '{text_model}': {e}")
                self.text_model = None
            try:
                self.img_model = SentenceTransformer(img_model, device=device)
            except Exception as e:
                print(f"Failed to load image embedding model '{img_model}': {e}")
                self.img_model = None

    def _get_or_create_collection(self, name: str):
        try:
            return self.client.get_collection(name=name)
        except Exception:
            return self.client.create_collection(name=name)

    # ----------------
    # Embedding helpers
    # ----------------
    def embed_text(self, texts: List[str]) -> List[List[float]]:
        if self.text_model is None:
            raise RuntimeError("Text embedding model not available")
        embeddings = self.text_model.encode(texts, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist() if hasattr(embeddings, 'tolist') else list(embeddings)

    def embed_images(self, images: List):
        if self.img_model is None:
            raise RuntimeError("Image embedding model not available")
        emb = self.img_model.encode(images, batch_size=8, convert_to_numpy=True, normalize_embeddings=True)
        return emb.tolist() if hasattr(emb, 'tolist') else list(emb)

    # ----------------
    # Upsert functions
    # ----------------
    def upsert_text(self, doc_id: str, chunks: List[str], metadata: Optional[Dict] = None):
        if not chunks:
            return []
        if metadata is None:
            metadata = {}
        embeddings = self.embed_text(chunks)
        ids = [f"{doc_id}_t_{i}" for i in range(len(chunks))]
        self.text_collection.upsert(ids=ids, embeddings=embeddings, metadatas=[metadata]*len(chunks), documents=chunks)
        return ids

    def upsert_table(self, doc_id: str, csv_path: str, metadata: Optional[Dict] = None):
        if pd is None:
            raise RuntimeError("pandas is required to ingest tables")
        df = pd.read_csv(csv_path)
        rows = []
        for i in range(len(df)):
            row = df.iloc[i]
            row_text = " | ".join([f"{k}: {row[k]}" for k in row.index])
            rows.append(row_text)
        embeddings = self.embed_text(rows)
        ids = [f"{doc_id}_row_{i}" for i in range(len(rows))]
        if metadata is None:
            metadata = {}
        self.table_collection.upsert(ids=ids, embeddings=embeddings, metadatas=[metadata]*len(rows), documents=rows)
        return ids

    def upsert_image(self, doc_id: str, image_path: str, metadata: Optional[Dict] = None):
        if Image is None or np is None:
            raise RuntimeError("Pillow and numpy are required to ingest images")
        img = Image.open(image_path).convert("RGB")
        arr = np.array(img)
        emb = self.embed_images([arr])
        if metadata is None:
            metadata = {}
        self.image_collection.upsert(ids=[f"{doc_id}_img"], embeddings=emb, metadatas=[metadata], documents=[image_path])
        return [f"{doc_id}_img"]

    # ----------------
    # PDF ingestion
    # ----------------
    def ingest_pdf(self, doc_id_prefix: str, pdf_path: str, metadata: Optional[Dict] = None, chunk_pages: bool = True):
        """Extract text from PDF and upsert as text chunks.

        Uses PyMuPDF (fitz) if available, otherwise falls back to PyPDF2.
        Each page is inserted as a chunk when chunk_pages=True.
        """
        if metadata is None:
            metadata = {}

        text_chunks = []
        if fitz is not None:
            try:
                doc = fitz.open(pdf_path)
                for page in doc:
                    text = page.get_text("text")
                    if text and text.strip():
                        text_chunks.append(text)
            except Exception as e:
                print(f"fitz failed to read {pdf_path}: {e}")

        if not text_chunks and PdfReader is not None:
            try:
                reader = PdfReader(pdf_path)
                for p in reader.pages:
                    try:
                        t = p.extract_text() or ""
                    except Exception:
                        t = ""
                    if t.strip():
                        text_chunks.append(t)
            except Exception as e:
                print(f"PyPDF2 failed to read {pdf_path}: {e}")

        if not text_chunks:
            print(f"No text extracted from PDF: {pdf_path}")
            return []

        ids = []
        # upsert each chunk
        for i, chunk in enumerate(text_chunks):
            cid = f"{doc_id_prefix}_p_{i}"
            self.upsert_text(cid, [chunk], {**metadata, "source": os.path.basename(pdf_path)})
            ids.append(cid)

        return ids


def _hash_content(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    # Simple CLI: ingest two sample PDFs if they exist under backend/app/data or backend/data
    ingestor = Ingestor()
    possible = [
        os.path.join(os.getcwd(), "backend", "app", "data", "patient_diagnoses_medical_jargon.pdf"),
        os.path.join(os.getcwd(), "backend", "app", "data", "doctor_profiles_refined.pdf"),
        os.path.join(os.getcwd(), "backend", "data", "patient_diagnoses_medical_jargon.pdf"),
        os.path.join(os.getcwd(), "backend", "data", "doctor_profiles_refined.pdf"),
    ]
    for p in possible:
        if os.path.exists(p):
            print(f"Ingesting PDF: {p}")
            ids = ingestor.ingest_pdf(_hash_content(p), p)
            print(f"Inserted {len(ids)} chunks from {p}")