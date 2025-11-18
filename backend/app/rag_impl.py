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

# --- Embedded ingestion & retrieval helpers (merged from rag_pipeline/ingest_all.py & retriever.py)
import hashlib
import pandas as pd
try:
    from PIL import Image
except Exception:
    Image = None


def _hash_content(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


class ChromaIngestor:
    """Lightweight ingestor that uses an existing chroma client and an embedding model.

    Features: upsert_text, upsert_table (CSV), upsert_image, ingest_pdf.
    """

    def __init__(self, client: chromadb.Client, embedding_model: SentenceTransformer, persist_dir: Optional[str] = None):
        self.client = client
        self.embedding_model = embedding_model
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
        arr = np.array(img)
        # For simplicity embed the image via text-model encode of filename (placeholder)
        emb = self.embed_text([os.path.basename(image_path)])
        if metadata is None:
            metadata = {}
        self.image_collection.upsert(ids=[f"{doc_id}_img"], embeddings=emb, metadatas=[metadata], documents=[image_path])
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

        # Initialize pipeline helpers (ingestor + retriever) merged from rag_pipeline
        self.ingestor = ChromaIngestor(self.client, self.embedding_model)
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
        """Ingest local PDF files if present in backend/app/data/pdf or backend/data."""
        # Look for specific named PDFs first
        candidates = []
        possible_paths = [
            os.path.join(os.getcwd(), "backend", "app", "data", "patient_diagnoses_medical_jargon.pdf"),
            os.path.join(os.getcwd(), "backend", "app", "data", "doctor_profiles_refined.pdf"),
            os.path.join(os.getcwd(), "backend", "data", "patient_diagnoses_medical_jargon.pdf"),
            os.path.join(os.getcwd(), "backend", "data", "doctor_profiles_refined.pdf"),
        ]
        # Also ingest any PDFs under backend/app/data
        candidates += [p for p in possible_paths if os.path.exists(p)]
        candidates += glob.glob(os.path.join(os.getcwd(), "backend", "app", "data", "*.pdf"))

        if not candidates:
            print("No local PDFs found to ingest.")
            return

        for path in sorted(set(candidates)):
            try:
                meta = {"source_file": os.path.basename(path)}
                if "patient" in os.path.basename(path).lower():
                    meta["type"] = "patient_pdf"
                elif "doctor" in os.path.basename(path).lower():
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
        max_results: int = 3
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
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []
        
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
        
        # Generate answer based on retrieved documents
        answer = self._generate_answer(question, documents, metadatas)
        
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
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence
        }
    
    def _generate_answer(
        self,
        question: str,
        documents: List[str],
        metadatas: List[Dict]
    ) -> str:
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
        
        if not documents:
            return "I don't have enough information to answer that question."
        
        # Combine information from top documents
        combined_info = "\n\n".join(documents[:2])  # Use top 2 most relevant
        
        # Create a simple answer
        answer = f"Based on the available healthcare information:\n\n{combined_info}"
        
        # Add metadata context if available
        conditions = [m.get('condition', '') for m in metadatas if m.get('condition')]
        if conditions:
            answer += f"\n\nRelated conditions: {', '.join(set(conditions))}"
        
        return answer

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

