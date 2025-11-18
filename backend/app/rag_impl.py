"""
Healthcare RAG System Implementation
Handles document retrieval and answer generation for healthcare queries.
"""

import os
import glob
import requests
from typing import Any, List, Dict, Optional, Tuple
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
import re
import json
from .model_manager import ModelManager

# --- Embedded ingestion & retrieval helpers (merged from rag_pipeline/ingest_all.py & retriever.py)
import hashlib
import pandas as pd
try:
    from PIL import Image
except Exception:
    Image = None
try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except Exception:
    CROSS_ENCODER_AVAILABLE = False


def _hash_content(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


class ChromaIngestor:
    """Lightweight ingestor that uses an existing chroma client and an embedding model.

    Features: upsert_text, upsert_table (CSV), upsert_image, ingest_pdf.
    """

    def __init__(self, client: chromadb.Client, embedding_model: SentenceTransformer, persist_dir: Optional[str] = None, model_manager: Optional[ModelManager] = None):
        self.client = client
        self.embedding_model = embedding_model
        self.model_manager = model_manager
        # ensure collections exist
        self.text_collection = self._get_or_create_collection("text_docs")
        self.table_collection = self._get_or_create_collection("table_docs")
        self.image_collection = self._get_or_create_collection("image_docs")

    def _get_or_create_collection(self, name: str):
        try:
            return self.client.get_collection(name=name)
        except Exception:
            return self.client.create_collection(name=name)

    def embed_text(self, texts: List[str]):
        emb = self.embedding_model.encode(texts)
        try:
            return emb.tolist()
        except Exception:
            return [list(e) for e in emb]

    def upsert_text(self, doc_id: str, chunks: List[str], metadata: Optional[Dict] = None):
        if metadata is None:
            metadata = {}
        embeddings = self.embed_text(chunks)
        ids = [f"{doc_id}_t_{i}" for i in range(len(chunks))]
        self.text_collection.upsert(ids=ids, embeddings=embeddings, metadatas=[metadata] * len(chunks), documents=chunks)
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
        self.table_collection.upsert(ids=ids, embeddings=embeddings, metadatas=[metadata] * len(rows), documents=rows)
        return ids

    def upsert_image(self, doc_id: str, image_path: str, metadata: Optional[Dict] = None):
        if Image is None or np is None:
            raise RuntimeError("Pillow and numpy are required to ingest images")
        img = Image.open(image_path).convert("RGB")
        # Prefer using ModelManager's image embedder if available
        embeddings = None
        try:
            if self.model_manager is not None and hasattr(self.model_manager, 'embed_image'):
                img_emb = self.model_manager.embed_image(image_path)
                if img_emb is not None:
                    # ensure embeddings is a list-of-vectors for upsert
                    if isinstance(img_emb[0], (float, int)):
                        embeddings = [img_emb]
                    else:
                        embeddings = [list(img_emb)]
        except Exception:
            embeddings = None

        # Fallback: embed via text embedder on filename or a short caption
        if embeddings is None:
            caption = os.path.basename(image_path)
            embeddings = self.embed_text([caption])

        if metadata is None:
            metadata = {}
        self.image_collection.upsert(ids=[f"{doc_id}_img"], embeddings=embeddings, metadatas=[metadata], documents=[image_path])
        return [f"{doc_id}_img"]

    def ingest_pdf(self, doc_id_prefix: str, pdf_path: str, metadata: Optional[Dict] = None):
        """Extract text from PDF and upsert as text chunks using PyPDF2 if available."""
        try:
            from PyPDF2 import PdfReader
        except Exception:
            PdfReader = None
        if metadata is None:
            metadata = {}
        text_chunks = []
        # try PyMuPDF (fitz) first if available
        try:
            import fitz
            doc = fitz.open(pdf_path)
            for page in doc:
                text = page.get_text("text")
                if text and text.strip():
                    text_chunks.append(text)
        except Exception:
            pass

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
            except Exception:
                pass

        if not text_chunks:
            return []

        ids = []
        for i, chunk in enumerate(text_chunks):
            cid = f"{doc_id_prefix}_p_{i}"
            self.upsert_text(cid, [chunk], {**metadata, "source": os.path.basename(pdf_path)})
            ids.append(cid)
        return ids


class ChromaCollectionsRetriever:
    """Retrieve from multiple chroma collections by querying each collection with an embedding."""

    def __init__(self, client: chromadb.Client, collection_names: Optional[List[str]] = None):
        self.client = client
        if collection_names is None:
            collection_names = ["text_docs", "table_docs", "image_docs"]
        self.collection_names = collection_names

    def get_relevant_documents(self, query_embedding: List[float], k: int = 6):
        candidates = []
        for name in self.collection_names:
            try:
                col = self.client.get_collection(name=name)
            except Exception:
                continue
            try:
                res = col.query(query_embeddings=[query_embedding], n_results=k)
            except Exception:
                # Some chroma versions use slightly different kwargs; try again
                try:
                    res = col.query(query_embeddings=[query_embedding], n_results=k)
                except Exception:
                    continue

            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]
            for doc, meta, dist in zip(docs, metas, dists):
                candidates.append({"document": doc, "metadata": meta, "distance": dist})

        # dedupe by metadata id or hash
        seen = set()
        deduped = []
        for c in candidates:
            meta = c.get("metadata") or {}
            doc_id = meta.get("id") or meta.get("doc_id") or hash(c.get("document", ""))
            if doc_id in seen:
                continue
            seen.add(doc_id)
            deduped.append(c)
            if len(deduped) >= k:
                break
        return deduped

# --- End merged helpers


class HealthcareRAG:
    """
    RAG system for healthcare information retrieval.
    Uses ChromaDB for vector storage and semantic search.
    """
    
    def __init__(
        self,
        collection_name: str = "healthcare_documents",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the Healthcare RAG system
        
        Args:
            collection_name: Name of the ChromaDB collection
            embedding_model: Name of the sentence transformer model to use
        """
        self.collection_name = collection_name

        # Allow overriding embedding model and persist directory via environment
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", embedding_model)

        # Initialize embedding model
        print(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        # Initialize ChromaDB
        # Read persist dir from env to match docker-compose and avoid hard-coded paths
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./backend/data/chroma")
        # Avoid passing deprecated configuration keys to Settings; keep only persist_directory
        self.client = chromadb.Client(Settings(
            persist_directory=persist_dir
        ))
        
        # Get or create primary collection (used by some endpoints)
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Healthcare documents and knowledge base"}
            )
            print(f"Created new collection: {collection_name}")

        # Multimodal / model manager (handles LLM routing + optional image embed)
        try:
            self.model_manager = ModelManager(text_embedding_model=self.embedding_model)
        except Exception:
            self.model_manager = None

        # Initialize pipeline helpers (ingestor + retriever) merged from rag_pipeline
        self.ingestor = ChromaIngestor(self.client, self.embedding_model, model_manager=self.model_manager)
        self.retriever = ChromaCollectionsRetriever(self.client)

        # If the primary collection is empty, populate defaults and try ingest paths
        try:
            if getattr(self.collection, "count", lambda: 0)() == 0:
                print("Collection empty, adding sample and local data...")
                self._add_sample_data()
                self._ingest_local_pdfs()
                self._ingest_hf_datasets()
        except Exception:
            # ignore cases where count() is not supported
            pass

        # Build a BM25 side-index for sparse retrieval if rank_bm25 available
        try:
            self._bm25 = None
            self._bm25_corpus_ids = []
            self._bm25_docs = {}
            if BM25Okapi is not None:
                self._build_bm25_index()
        except Exception:
            self._bm25 = None

        # Reranker (cross-encoder) lazy init
        self.reranker = None
        self.reranker_name = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        try:
            self.rerank_topk = int(os.getenv("RERANK_TOPK", "50"))
        except Exception:
            self.rerank_topk = 50

        # Configure internet fallback (if enabled via env)
        self.allow_internet = os.getenv("USE_INTERNET", "false").lower() in ("1", "true", "yes")
    
    def _add_sample_data(self):
        """Add sample healthcare documents to the knowledge base"""
        sample_documents = [
            {
                "content": "Hypertension, also known as high blood pressure, is a condition where the force of blood against artery walls is consistently too high. Normal blood pressure is below 120/80 mmHg. Treatment includes lifestyle changes like diet, exercise, and medication such as ACE inhibitors or beta-blockers.",
                "metadata": {"category": "cardiovascular", "condition": "hypertension"}
            },
            {
                "content": "Type 2 diabetes is a chronic condition affecting how the body processes blood sugar (glucose). Symptoms include increased thirst, frequent urination, and fatigue. Management involves blood sugar monitoring, healthy eating, regular exercise, and medications like metformin or insulin if needed.",
                "metadata": {"category": "endocrine", "condition": "diabetes"}
            },
            {
                "content": "Asthma is a respiratory condition where airways narrow and swell, producing extra mucus. Common symptoms include wheezing, shortness of breath, chest tightness, and coughing. Treatment typically includes quick-relief inhalers (bronchodilators) and long-term control medications like inhaled corticosteroids.",
                "metadata": {"category": "respiratory", "condition": "asthma"}
            },
            {
                "content": "Depression is a mood disorder causing persistent feelings of sadness and loss of interest. Symptoms include low energy, sleep problems, and difficulty concentrating. Treatment options include psychotherapy (cognitive behavioral therapy), medications (SSRIs like sertraline), and lifestyle modifications.",
                "metadata": {"category": "mental_health", "condition": "depression"}
            },
            {
                "content": "Osteoarthritis is the most common form of arthritis, caused by wear and tear of joint cartilage. It commonly affects knees, hips, hands, and spine. Symptoms include joint pain, stiffness, and reduced flexibility. Treatment includes pain relievers, physical therapy, and in severe cases, joint replacement surgery.",
                "metadata": {"category": "musculoskeletal", "condition": "osteoarthritis"}
            },
            {
                "content": "Migraine headaches are severe, recurring headaches often accompanied by nausea, vomiting, and sensitivity to light and sound. They can last hours to days. Treatment includes pain-relieving medications (triptans), preventive medications (beta-blockers, anticonvulsants), and identifying trigger avoidance.",
                "metadata": {"category": "neurological", "condition": "migraine"}
            },
            {
                "content": "Gastroesophageal reflux disease (GERD) occurs when stomach acid frequently flows back into the esophagus. Symptoms include heartburn, chest pain, and difficulty swallowing. Treatment includes lifestyle changes, antacids, H2 blockers, or proton pump inhibitors like omeprazole.",
                "metadata": {"category": "digestive", "condition": "gerd"}
            },
            {
                "content": "Chronic kidney disease (CKD) is the gradual loss of kidney function over time. Early stages often have no symptoms. As it progresses, symptoms include fatigue, swelling, and changes in urination. Management focuses on treating underlying causes, controlling blood pressure, and in advanced stages, dialysis or transplant.",
                "metadata": {"category": "renal", "condition": "chronic_kidney_disease"}
            },
            {
                "content": "Atrial fibrillation (AFib) is an irregular and often rapid heart rhythm that can increase risk of stroke and heart failure. Symptoms include palpitations, fatigue, and shortness of breath. Treatment may include medications to control heart rate and rhythm, blood thinners to prevent stroke, and sometimes procedures like cardioversion or ablation.",
                "metadata": {"category": "cardiovascular", "condition": "atrial_fibrillation"}
            },
            {
                "content": "Allergic rhinitis (hay fever) is an allergic response causing sneezing, congestion, runny nose, and itchy eyes. It can be seasonal or year-round. Treatment includes avoiding allergens, antihistamines, nasal corticosteroids, and in some cases, immunotherapy (allergy shots).",
                "metadata": {"category": "immunological", "condition": "allergic_rhinitis"}
            }
        ]
        
        print("Adding sample healthcare documents...")
        for doc in sample_documents:
            doc_id = self.add_document(doc["content"], doc["metadata"])
            # Also add to text_docs collection for multi-collection retrieval
            try:
                self.ingestor.upsert_text(doc_id, [doc["content"]], metadata=doc["metadata"])
            except Exception:
                pass
        print(f"Added {len(sample_documents)} sample documents to knowledge base")

    def _ingest_local_pdfs(self):
        """Ingest local PDF files found under project data folders.

        This version searches recursively under `backend/app/data` and `backend/data` so
        PDFs placed in subdirectories (e.g. `backend/app/data/text/`) are discovered.
        """
        # candidate specific files to prefer
        specific_paths = [
            os.path.join(os.getcwd(), "backend", "app", "data", "patient_diagnoses_medical_jargon.pdf"),
            os.path.join(os.getcwd(), "backend", "app", "data", "doctor_profiles_refined.pdf"),
            os.path.join(os.getcwd(), "backend", "data", "patient_diagnoses_medical_jargon.pdf"),
            os.path.join(os.getcwd(), "backend", "data", "doctor_profiles_refined.pdf"),
        ]

        candidates = []
        candidates += [p for p in specific_paths if os.path.exists(p)]

        # Recursively find any PDFs under the app/data and data directories
        search_dirs = [
            os.path.join(os.getcwd(), "backend", "app", "data"),
            os.path.join(os.getcwd(), "backend", "data"),
        ]
        for d in search_dirs:
            if os.path.isdir(d):
                candidates += glob.glob(os.path.join(d, "**", "*.pdf"), recursive=True)

        # Deduplicate and filter
        candidates = sorted({p for p in candidates if os.path.exists(p)})

        if not candidates:
            print("No local PDFs found to ingest.")
            return

        for path in candidates:
            try:
                meta = {"source_file": os.path.basename(path)}
                name = os.path.basename(path).lower()
                if "patient" in name:
                    meta["type"] = "patient_pdf"
                elif "doctor" in name:
                    meta["type"] = "doctor_pdf"
                else:
                    meta["type"] = "pdf"
                print(f"Ingesting PDF {path} as {meta['type']}")
                ids = self.ingestor.ingest_pdf(_hash_content(path), path, metadata=meta)
                print(f"Inserted {len(ids)} chunks from {path}")
            except Exception as e:
                print(f"Failed to ingest {path}: {e}")

    def _ingest_hf_datasets(self):
        """Load datasets referenced in backend/app/data/tables/db.py and ingest small items as documents."""
        try:
            from backend.app.data.tables import db as hf_db
        except Exception:
            try:
                from backend.app.data.tables import db as hf_db  # try alternative import
            except Exception:
                hf_db = None

        if hf_db is None:
            # try to load datasets directly
            try:
                from datasets import load_dataset
                ds_qna = load_dataset("adrianf12/healthcare-qa-dataset")
                ds = load_dataset("deep-div/healthcare_terms_glossary")
            except Exception:
                print("Could not load HF datasets; skipping dataset ingestion.")
                return
        else:
            # the db.py module already loads datasets as ds_qna and ds if present
            ds_qna = getattr(hf_db, 'ds_qna', None)
            ds = getattr(hf_db, 'ds', None)

        # Ingest small items from ds (glossary) and ds_qna
        added = 0
        try:
            if ds is not None:
                for item in ds:
                    # ds can be a DatasetDict or IterableDataset; handle common cases
                    try:
                        text = item.get('definition') or item.get('term') or str(item)
                    except Exception:
                        text = str(item)
                    meta = {"type": "dataset_glossary", "source": "healthcare_terms_glossary"}
                    self.collection.add(
                        embeddings=[self.embedding_model.encode(text).tolist()],
                        documents=[text],
                        metadatas=[meta],
                        ids=[f"ds_glossary_{added}"]
                    )
                    added += 1
                    if added >= 50:
                        break
        except Exception:
            pass

        try:
            added_q = 0
            if ds_qna is not None:
                for item in ds_qna:
                    try:
                        q = item.get('question') or str(item)
                        a = item.get('answer') or ''
                        text = f"Q: {q}\nA: {a}"
                    except Exception:
                        text = str(item)
                    meta = {"type": "dataset_qna", "source": "healthcare_qa_dataset"}
                    self.collection.add(
                        embeddings=[self.embedding_model.encode(text).tolist()],
                        documents=[text],
                        metadatas=[meta],
                        ids=[f"ds_qna_{added_q}"]
                    )
                    added_q += 1
                    if added_q >= 50:
                        break
        except Exception:
            pass

        # --- New: ingest the 'aldsouza/healthcare-api-tool-calling' dataset if available
        try:
            added_api = 0
            try:
                from datasets import load_dataset
                ds_api = load_dataset("aldsouza/healthcare-api-tool-calling")
            except Exception:
                ds_api = None

            if ds_api is not None:
                # ds_api might be a DatasetDict; try to iterate over its splits
                def iter_dataset(dset):
                    if isinstance(dset, dict):
                        for split in dset.values():
                            for item in split:
                                yield item
                    else:
                        for item in dset:
                            yield item

                citation = "@dataset{healthcare_api_tool_calling,\n  title={Healthcare API Tool Calling Dataset},\n  author={Your Name},\n  year={2024},\n  url={https://huggingface.co/datasets/your-username/healthcare-api-tool-calling}\n}"

                for item in iter_dataset(ds_api):
                    try:
                        # The dataset schema may vary; pick sensible fields if present
                        prompt = item.get('input') or item.get('prompt') or item.get('question') or str(item)
                        output = item.get('output') or item.get('response') or item.get('answer') or ''
                        text = f"Prompt: {prompt}\n\nResponse: {output}"
                    except Exception:
                        text = str(item)

                    meta = {
                        "type": "dataset_tool_calling",
                        "source": "aldsouza/healthcare-api-tool-calling",
                        "citation": citation,
                    }

                    # Add to collection
                    try:
                        emb = self.embedding_model.encode(text).tolist()
                    except Exception:
                        emb = self.embedding_model.encode(text)
                    self.collection.add(
                        embeddings=[emb],
                        documents=[text],
                        metadatas=[meta],
                        ids=[f"ds_api_{added_api}"]
                    )
                    added_api += 1
                    if added_api >= 200:
                        break
                print(f"Ingested {added_api} items from aldsouza/healthcare-api-tool-calling")
        except Exception:
            # Ignore dataset ingestion failures; non-critical
            pass

    def _build_bm25_index(self):
        """Build a lightweight BM25 index from the primary collection documents.

        This builds an in-memory BM25 index (rank_bm25.BM25Okapi) and maps ids -> (text, metadata).
        It is used as a sparse retrieval signal fused with dense retrieval from Chroma.
        """
        try:
            # attempt to fetch all documents from the primary collection
            try:
                items = self.collection.get()
            except Exception:
                # older/newer chroma clients may require explicit kwargs
                try:
                    items = self.collection.get(include=['documents','metadatas','ids'])
                except Exception:
                    items = None

            docs = []
            ids = []
            metadatas = []
            if items:
                # items expected to be a dict with keys 'documents','metadatas','ids'
                docs = items.get('documents', [])
                metadatas = items.get('metadatas', [])
                ids = items.get('ids', [])

            # normalize to lists
            flat_docs = []
            flat_ids = []
            flat_metas = []
            # items may be nested; try to flatten defensively
            if isinstance(docs, list) and docs:
                # if docs is list-of-lists, flatten
                if any(isinstance(d, list) for d in docs):
                    for group, midx in zip(docs, metadatas if metadatas else [{}]*len(docs)):
                        # group may be list
                        for i, d in enumerate(group):
                            flat_docs.append(d)
                            # align ids if available
                            if ids:
                                try:
                                    flat_ids.append(ids.pop(0))
                                except Exception:
                                    flat_ids.append(f"doc_{len(flat_ids)}")
                            else:
                                flat_ids.append(f"doc_{len(flat_ids)}")
                            flat_metas.append((midx if isinstance(midx, dict) else {}))
                else:
                    flat_docs = docs
                    flat_ids = ids if ids else [f"doc_{i}" for i in range(len(docs))]
                    flat_metas = metadatas if metadatas else [{} for _ in flat_docs]

            # Build tokenized corpus
            tokenized = []
            for i, text in enumerate(flat_docs):
                txt = text if isinstance(text, str) else str(text)
                tokens = txt.split()
                tokenized.append(tokens)
                self._bm25_docs[flat_ids[i]] = {'text': txt, 'metadata': flat_metas[i]}
                self._bm25_corpus_ids.append(flat_ids[i])

            if tokenized and BM25Okapi is not None:
                try:
                    self._bm25 = BM25Okapi(tokenized)
                    print(f"Built BM25 index with {len(tokenized)} documents")
                except Exception as e:
                    print(f"Failed to build BM25 index: {e}")
                    self._bm25 = None
        except Exception as e:
            print(f"BM25 build error: {e}")
            self._bm25 = None
    
    def add_document(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a document to the knowledge base
        
        Args:
            content: Document content
            metadata: Optional metadata for the document
            
        Returns:
            Document ID
        """
        if metadata is None:
            metadata = {}
        
        # Generate embedding
        embedding = self.embedding_model.encode(content).tolist()
        
        # Generate unique ID
        doc_id = f"doc_{hash(content) % 10**8}"
        
        # Add to collection
        self.collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        return doc_id
    
    def query(
        self,
        question: str,
        max_results: int = 3,
        images: Optional[List[str]] = None,
        rerank: bool = True,
    ) -> Dict:
        """
        Query the knowledge base and generate an answer
        
        Args:
            question: User's question
            max_results: Maximum number of relevant documents to retrieve
            
        Returns:
            Dictionary with answer, sources, and confidence
        """
        # Decide retrieval strategy based on simple intent/rule routing
        q_lower = question.lower()
        where_filter = None

        # Priority routing rules
        if any(k in q_lower for k in ("patient information", "patient", "diagnos", "medical record", "medical jargon")):
            where_filter = {"type": "patient_pdf"}
        elif any(k in q_lower for k in ("match doctor", "match a doctor", "find a doctor", "doctor profile", "which doctor", "referral", "assign doctor")):
            where_filter = {"type": "doctor_pdf"}
        elif any(k in q_lower for k in ("jargon", "what does", "meaning of", "glossary", "terms", "common question", "faq")):
            where_filter = {"type": "dataset_glossary"}

        # Generate query embedding
        query_embedding = self.embedding_model.encode(question).tolist()

        # Search for relevant documents. Try to use metadata filter if collection supports it.
        try:
            if where_filter is not None:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=max_results,
                    where=where_filter
                )
            else:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=max_results
                )
        except TypeError:
            # Older chroma clients may not support 'where' kwarg; fall back to unfiltered query
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results
            )
        except Exception as e:
            print(f"Chroma query failed: {e}")
            results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        
        # Extract results
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]

        # Filter out known noisy dataset/tool-calling artifacts by default.
        # These datasets can contain system prompts and tool-calling examples that
        # are not useful as factual sources for general user questions.
        try:
            filtered_docs = []
            filtered_metas = []
            filtered_dists = []
            for doc, meta, dist in zip(documents, metadatas, distances):
                mtype = (meta or {}).get('type') if isinstance(meta, dict) else None
                src = (meta or {}).get('source') if isinstance(meta, dict) else None
                # textual heuristics: many tool-calling dataset items include prompts
                doc_text = doc if isinstance(doc, str) else ''
                noisy_textual = False
                lt = doc_text.lower()
                if 'prompt:' in lt or 'you are an intelligent ai assistant' in lt or 'messages' in lt:
                    noisy_textual = True

                if mtype == 'dataset_tool_calling' or (isinstance(src, str) and 'healthcare-api-tool-calling' in src) or noisy_textual:
                    # skip these noisy examples unless they are the only results
                    continue
                filtered_docs.append(doc)
                filtered_metas.append(meta)
                filtered_dists.append(dist)

            # If filtering removed everything, fall back to original results
            if filtered_docs:
                documents, metadatas, distances = filtered_docs, filtered_metas, filtered_dists
        except Exception:
            pass
        
        if not documents:
            # If nothing found locally and internet fallback is allowed, try a web lookup
            if self.allow_internet:
                web_answer, web_source = self._search_internet(question)
                return {
                    "answer": web_answer,
                    "sources": [{"content": web_source, "metadata": {"source": "internet"}, "relevance_score": 0.0}],
                    "confidence": 0.0
                }

            return {
                "answer": "I couldn't find relevant information to answer your question. Please try rephrasing or ask about a different topic.",
                "sources": [],
                "confidence": 0.0
            }
        # If BM25 side-index exists, compute sparse scores and fuse with dense
        fused_candidates = None
        try:
            if getattr(self, '_bm25', None) is not None and self._bm25 is not None:
                # compute sparse scores
                q_tokens = question.split()
                sparse_scores = self._bm25.get_scores(q_tokens)
                # map sparse scores to ids
                sparse_list = []
                for idx, sid in enumerate(self._bm25_corpus_ids):
                    # Skip BM25 entries that appear to be noisy tool-calling examples
                    try:
                        bm_meta = self._bm25_docs.get(sid, {}).get('metadata', {})
                        bm_type = bm_meta.get('type') if isinstance(bm_meta, dict) else None
                        bm_src = bm_meta.get('source') if isinstance(bm_meta, dict) else None
                        if bm_type == 'dataset_tool_calling' or (isinstance(bm_src, str) and 'healthcare-api-tool-calling' in bm_src):
                            continue
                        # also skip textual prompts
                        bm_text = self._bm25_docs.get(sid, {}).get('text', '')
                        if isinstance(bm_text, str) and ('prompt:' in bm_text.lower() or 'you are an intelligent ai assistant' in bm_text.lower()):
                            continue
                    except Exception:
                        pass
                    sparse_list.append({'id': sid, 'score': float(sparse_scores[idx])})

                # dense results -> ids and dense scores (convert distances to similarity)
                dense_list = []
                # we need ids for dense results; try to obtain them from metadatas if present
                for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
                    did = None
                    if isinstance(meta, dict):
                        did = meta.get('id') or meta.get('doc_id')
                    if did is None:
                        # fallback to hashing document
                        did = _hash_content(doc)
                    dense_list.append({'id': did, 'score': float(1.0 / (1.0 + float(dist))) if dist is not None else 0.0, 'document': doc, 'metadata': meta})

                # build a candidate union of ids
                candidate_ids = {d['id'] for d in dense_list}
                candidate_ids.update({s['id'] for s in sparse_list})

                # build score maps
                dense_map = {d['id']: d['score'] for d in dense_list}
                sparse_map = {s['id']: s['score'] for s in sparse_list}

                # normalize scores
                def _normalize(m):
                    if not m:
                        return {}
                    vals = list(m.values())
                    mx = max(vals)
                    mn = min(vals)
                    rng = mx - mn if mx != mn else 1.0
                    return {k: (v - mn) / rng for k, v in m.items()}

                dense_norm = _normalize(dense_map)
                sparse_norm = _normalize(sparse_map)

                alpha = 0.7
                fused = []
                for cid in candidate_ids:
                    dsc = dense_norm.get(cid, 0.0)
                    ssc = sparse_norm.get(cid, 0.0)
                    fused_score = alpha * dsc + (1 - alpha) * ssc
                    # resolve document & metadata: prefer dense_list info
                    doc_text = None
                    meta = {}
                    if cid in dense_map:
                        for d in dense_list:
                            if d['id'] == cid:
                                doc_text = d.get('document')
                                meta = d.get('metadata') or {}
                                break
                    if doc_text is None and cid in self._bm25_docs:
                        doc_text = self._bm25_docs[cid]['text']
                        meta = self._bm25_docs[cid].get('metadata', {})

                    fused.append({'id': cid, 'score': fused_score, 'document': doc_text, 'metadata': meta})

                # sort fused candidates (before reranking)
                fused_candidates = sorted([c for c in fused if c.get('document')], key=lambda x: x['score'], reverse=True)
                # If reranker available, we'll rerank a larger pool later; for now keep the full fused list
                # (we'll trim after reranking)
        except Exception:
            fused_candidates = None

        # If fusion produced candidates, use them as documents; else fall back to dense results
        reranked_used = False
        if fused_candidates:
            # Optionally rerank fused candidates with a cross-encoder for better precision
            try:
                # lazy load reranker
                if rerank and getattr(self, 'reranker', None) is None and CROSS_ENCODER_AVAILABLE:
                    try:
                        self.reranker = CrossEncoder(self.reranker_name)
                    except Exception:
                        # keep None if loading fails
                        self.reranker = None

                reranked = None
                if rerank and getattr(self, 'reranker', None) is not None:
                    # build a candidate pool up to rerank_topk
                    pool = fused_candidates[: max(len(fused_candidates), self.rerank_topk)]
                    texts = [c['document'] for c in pool]
                    pairs = [[question, t] for t in texts]
                    try:
                        scores = self.reranker.predict(pairs)
                        # attach scores and sort
                        for i, sc in enumerate(scores):
                            pool[i]['rerank_score'] = float(sc)
                        reranked = sorted(pool, key=lambda x: x.get('rerank_score', 0.0), reverse=True)
                        reranked_used = True
                    except Exception:
                        reranked = None

                final_candidates = reranked if reranked is not None else fused_candidates

                # limit to max_results
                final_candidates = final_candidates[:max_results]

                documents = [c['document'] for c in final_candidates]
                metadatas = [c.get('metadata', {}) for c in final_candidates]
                # distances aren't meaningful after fusion/rerank; create proxy distances from fused or rerank score
                distances = []
                for c in final_candidates:
                    if 'rerank_score' in c:
                        # higher rerank_score -> lower distance proxy
                        distances.append(1.0 / max(1e-6, c.get('rerank_score')) - 1.0)
                    else:
                        distances.append(1.0 / max(1e-6, c.get('score')) - 1.0)
            except Exception:
                documents = [c['document'] for c in fused_candidates]
                metadatas = [c.get('metadata', {}) for c in fused_candidates]
                distances = [1.0 / max(1e-6, c['score']) - 1.0 for c in fused_candidates]
        else:
            reranked_used = False
        # Telemetry: record reranker scores & selection if enabled
        telemetry = None
        try:
            if os.getenv("ENABLE_TELEMETRY", "false").lower() in ("1", "true", "yes"):
                telemetry = {"reranked": bool(reranked_used)}
                # include top-k reranker scores if available
                if reranked_used and 'reranked' in locals() and reranked is not None:
                    telemetry_scores = []
                    for c in (reranked[: self.rerank_topk]):
                        telemetry_scores.append({"id": c.get('id'), "rerank_score": float(c.get('rerank_score', 0.0))})
                    telemetry["reranker_scores"] = telemetry_scores
                elif fused_candidates:
                    # include fused top-k scores
                    telemetry_scores = []
                    for c in (fused_candidates[: self.rerank_topk]):
                        telemetry_scores.append({"id": c.get('id'), "fused_score": float(c.get('score', 0.0))})
                    telemetry["fused_scores"] = telemetry_scores
                # append to a local telemetry log file for offline analysis
                try:
                    os.makedirs(os.path.join(os.getcwd(), "backend", "data"), exist_ok=True)
                    tpath = os.path.join(os.getcwd(), "backend", "data", "telemetry.log")
                    with open(tpath, "a") as fh:
                        fh.write(json.dumps({"question": question, "telemetry": telemetry}) + "\n")
                except Exception:
                    pass
        except Exception:
            telemetry = None
        # Generate answer based on retrieved documents (also capture model used)
        answer, used_model = self._generate_answer(question, documents, metadatas, images=images)

        # Decide which model was used: prefer the model reported by the generator (used_model),
        # else fall back to the ModelManager configured LLM or to the embedding model.
        model_name = None
        if used_model:
            model_name = used_model
        else:
            try:
                if getattr(self, 'model_manager', None) is not None:
                    model_name = getattr(self.model_manager, 'llm_model_name', None) or None
            except Exception:
                model_name = None
        if not model_name:
            model_name = getattr(self, 'embedding_model_name', None)

        # Format sources
        sources = []
        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            sources.append({
                "content": doc[:200] + "..." if len(doc) > 200 else doc,
                "metadata": metadata,
                "relevance_score": float(1 / (1 + distance))  # Convert distance to similarity
            })

        # Calculate confidence (based on relevance of top result)
        confidence = float(1 / (1 + distances[0])) if distances else 0.0
    # Guardrails: enforce a minimum citation / evidence threshold
        try:
            threshold = float(os.getenv("CITATION_THRESHOLD", "0.25"))
        except Exception:
            threshold = 0.25

        disclaimer = os.getenv("ANSWER_DISCLAIMER", "I may be incorrect — consult a clinician for medical advice.")

        if confidence < threshold:
            # Not enough evidence to provide a grounded answer
            no_answer = (
                "I don't have sufficient reliable information in the knowledge base to confidently answer that question. "
                f"{disclaimer}"
            )
            return {
                "answer": no_answer,
                "sources": sources,
                "confidence": confidence,
                "model": model_name,
                "no_answer": True,
                "reranked": reranked_used
            }

        # Ensure the answer includes an explicit citations section. If the generator returned text
        # without citations, append a citations block derived from the sources we retrieved.
        try:
            # If answer already contains the word 'Citation' or 'Source', assume it has citations
            if isinstance(answer, str) and not ("Citation" in answer or "citation" in answer or "Source:" in answer or "Sources:" in answer):
                citation_lines = []
                for s in sources:
                    meta = s.get("metadata") or {}
                    cite = meta.get("citation") or meta.get("source") or meta.get("source_file") or meta.get("doc_id") or meta.get("id")
                    snippet = (s.get("content") or "")[:200]
                    if cite:
                        citation_lines.append(f"- {cite}: {snippet}")
                    else:
                        citation_lines.append(f"- {meta.get('type','source')}: {snippet}")
                if citation_lines:
                    answer = f"{answer}\n\nCitations:\n" + "\n".join(citation_lines)
                else:
                    # If no structured citation metadata available, still append short snippets
                    short_snips = [f"- {s.get('content')[:120]}" for s in sources[:3] if s.get('content')]
                    if short_snips:
                        answer = f"{answer}\n\nCitations (snippets):\n" + "\n".join(short_snips)
        except Exception:
            # If citation appending fails for any reason, fall back to returning the raw answer
            pass

        result = {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "model": model_name,
            "no_answer": False,
            "reranked": reranked_used
        }
        if telemetry is not None:
            result["telemetry"] = telemetry
        return result
    
    def _generate_answer(
        self,
        question: str,
        documents: List[str],
        metadatas: List[Dict]
        , images: Optional[List[str]] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Generate an answer based on retrieved documents
        
        Args:
            question: User's question
            documents: Retrieved relevant documents
            metadatas: Metadata for retrieved documents
            
        Returns:
            Generated answer
        """
        # Simple answer generation by combining relevant information
        # In a production system, this would use an LLM like GPT-4

        # Filter out noisy retrieved documents that look like tool-calling prompts
        try:
            clean_docs = []
            clean_metas = []
            for doc, meta in zip(documents, metadatas):
                txt = doc if isinstance(doc, str) else ''
                lt = txt.lower()
                if 'prompt:' in lt or 'you are an intelligent ai assistant' in lt or 'messages' in lt:
                    continue
                clean_docs.append(doc)
                clean_metas.append(meta)
            if clean_docs:
                documents, metadatas = clean_docs, clean_metas
        except Exception:
            pass

        if not documents:
            return "I don't have enough information to answer that question.", None
        
    # Attempt to use a model manager (LLM) for a better multimodal answer.
        conditions = [m.get('condition', '') for m in metadatas if m.get('condition')]
        try:
            if self.model_manager is not None:
                # Build a compact prompt with the question + top documents
                top_text = "\n\n".join(documents[:4])
                meta_ctx = f"Related conditions: {', '.join(set(conditions))}" if conditions else ""

                # --- Few-shot augmentation: find similar tool-calling examples from ingested dataset
                few_shot_examples = []
                try:
                    q_emb = self.embedding_model.encode(question).tolist()
                    try:
                        ex_results = self.collection.query(query_embeddings=[q_emb], n_results=3, where={"type": "dataset_tool_calling"})
                    except TypeError:
                        # Older chroma clients may not support 'where'
                        ex_results = self.collection.query(query_embeddings=[q_emb], n_results=3)
                    except Exception:
                        ex_results = {"documents": [[]]}

                    ex_docs = ex_results.get("documents", [[]])[0] if ex_results else []
                    for ed in ex_docs:
                        # ed expected like: "Prompt: ...\n\nResponse: ..."
                        if not ed:
                            continue
                        few_shot_examples.append(ed)
                except Exception:
                    few_shot_examples = []

                examples_text = ""
                if few_shot_examples:
                    ex_lines = []
                    for ex in few_shot_examples[:3]:
                        ex_lines.append("---")
                        ex_lines.append(ex)
                    examples_text = "\n\nExamples:\n" + "\n".join(ex_lines) + "\n\n"

                prompt = (
                    f"You are a helpful medical assistant. Answer the question concisely.\n\n"
                    f"{examples_text}Question: {question}\n\nContext:\n{top_text}\n\n{meta_ctx}\n\nAnswer:"
                )
                gen_out = self.model_manager.generate_answer(prompt, max_tokens=256, images=images)
                # gen_out may be (text, model_name) or a plain string in older implementations
                if isinstance(gen_out, tuple):
                    answer_text, gen_model = gen_out
                else:
                    answer_text, gen_model = gen_out, None

                # If the generator returned something that appears to be the LLM fallback
                # (a local echo rather than a real generated answer), ignore it so we
                # fall back to a document-grounded synthesis below.
                if isinstance(answer_text, str) and answer_text.strip().startswith("[Local fallback answer]"):
                    # treat as no-model-available
                    answer_text = None
                    gen_model = None

                # If the generator returned a real-looking answer, return it
                if answer_text and isinstance(answer_text, str) and len(answer_text.strip()) > 0:
                    return answer_text, gen_model
        except Exception:
            # fall back to simpler answer if LLM generation fails
            pass

        # Fallback: combine information from top documents
        # Build a compact, evidence-grounded synthesis from retrieved documents.
        def extract_relevant_sentences(text, query_terms, max_sents=2):
            # split into sentences (rough heuristic)
            sents = re.split(r'(?<=[.!?])\s+', text.strip())
            selected = []
            lowered = text.lower()
            # prefer sentences containing query terms
            for sent in sents:
                if len(selected) >= max_sents:
                    break
                for t in query_terms:
                    if t in sent.lower():
                        selected.append(sent.strip())
                        break
            # fallback: take first sentences if none matched
            if not selected:
                for sent in sents[:max_sents]:
                    if sent.strip():
                        selected.append(sent.strip())
            return selected[:max_sents]

        query_terms = [t.lower() for t in re.findall(r"\w+", question) if len(t) > 3][:8]
        pieces = []
        breakdown = []
        for i, doc in enumerate(documents[:6]):
            txt = doc if isinstance(doc, str) else str(doc)
            sents = extract_relevant_sentences(txt, query_terms, max_sents=2)
            if sents:
                pieces.append(' '.join(sents))
            # include a short snippet and metadata reference
            meta = metadatas[i] if i < len(metadatas) else {}
            ref = meta.get('source') or meta.get('source_file') or meta.get('doc_id') or meta.get('id') or meta.get('type') or f'doc_{i}'
            snippet = (txt[:200] + '...') if len(txt) > 200 else txt
            breakdown.append(f"Source {i+1} ({ref}): {snippet}")

        summary = ' '.join(pieces) if pieces else (documents[0] if documents else '')
        answer_lines = ["Based on the retrieved documents, here is a concise summary:", "", summary]
        if conditions:
            answer_lines.append("")
            answer_lines.append("Related conditions: " + ', '.join(sorted(set(conditions))))

        answer_lines.append("")
        answer_lines.append("Breakdown by source:")
        answer_lines.extend(breakdown[:6])

        answer = '\n'.join(answer_lines)
        return answer, None

    def _search_internet(self, query: str) -> Tuple[str, str]:
        """
        Very small internet lookup using Wikipedia (open API).
        Returns (answer_text, source_url_or_snippet).
        """
        try:
            # Use MediaWiki opensearch to find a likely page
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {"action": "opensearch", "search": query, "limit": 1, "namespace": 0, "format": "json"}
            resp = requests.get(search_url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if len(data) >= 2 and data[1]:
                title = data[1][0]
                # Fetch summary
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.requote_uri(title)}"
                s = requests.get(summary_url, timeout=5)
                s.raise_for_status()
                sd = s.json()
                extract = sd.get("extract") or sd.get("title") or ""
                source = sd.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{requests.utils.requote_uri(title)}"
                answer = f"According to Wikipedia ({title}):\n\n{extract}"
                return answer, source
            else:
                return ("I couldn't find a good internet summary for that query.", "internet")
        except Exception as e:
            print(f"Internet search failed: {e}")
            return ("Internet lookup failed or not available.", "internet")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the knowledge base
        
        Returns:
            Dictionary with statistics
        """
        try:
            count = self.collection.count()
            return {
                "document_count": count,
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model_name,
                "status": "active"
            }
        except Exception as e:
            # Log the error but don't expose details in response
            print(f"Error getting stats: {str(e)}")
            return {
                "document_count": 0,
                "status": "error"
            }

