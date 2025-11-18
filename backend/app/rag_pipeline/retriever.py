"""Retriever wrapper using LangChain MultiVectorRetriever and Chroma.

This module reads the CHROMA_PERSIST_DIR env var (falling back to backend/data/chroma)
so it uses the same persist directory as the rest of the backend.
"""
import os

# LangChain import compatibility: modern LangChain v1+ splits and renames many
# modules. Try the most common locations and fall back to compatibility packages
# that are often installed (langchain_classic, langchain_core, langchain_community).
try:
    # preferred v1+ style (some installs expose these)
    from langchain.retrievers.multi_vector import MultiVectorRetriever
except Exception:
    try:
        from langchain_classic.retrievers.multi_vector import MultiVectorRetriever
    except Exception:
        # last-resort: import from core package if available
        from langchain_core.retrievers.multi_vector import MultiVectorRetriever

try:
    from langchain.storage import InMemoryByteStore
except Exception:
    try:
        from langchain_classic.storage import InMemoryByteStore
    except Exception:
        from langchain_core.stores import InMemoryByteStore

try:
    from langchain.docstore.document import Document
except Exception:
    try:
        from langchain_community.docstore.document import Document
    except Exception:
        from langchain_core.documents import Document

from langchain_community.vectorstores import Chroma


PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", os.path.join(os.getcwd(), "backend", "data", "chroma"))

# Wrap Chroma collections with LangChain VectorStore interfaces
text_vs = Chroma(collection_name="text_docs", persist_directory=PERSIST_DIR)
image_vs = Chroma(collection_name="image_docs", persist_directory=PERSIST_DIR)
table_vs = Chroma(collection_name="table_docs", persist_directory=PERSIST_DIR)

# Byte store for parent docs (may be unused depending on ingestion pipeline)
byte_store = None
try:
    byte_store = InMemoryByteStore()
except Exception:
    byte_store = None


class MultiCollectionRetriever:
    """Lightweight retriever that queries multiple LangChain-compatible
    VectorStore objects and merges/deduplicates results.

    This avoids tight coupling to a specific LangChain MultiVectorRetriever
    implementation which varies across LangChain versions.
    """

    def __init__(self, vectorstores, byte_store=None, id_key="doc_id"):
        self.vectorstores = vectorstores
        self.byte_store = byte_store
        self.id_key = id_key

    def get_relevant_documents(self, query, k: int = 6):
        results = []
        # Collect candidate documents from each vectorstore
        for vs in self.vectorstores:
            try:
                # Common Lanchain VectorStore API
                docs = vs.similarity_search(query, k=k)
                results.extend(docs)
            except Exception:
                try:
                    # Some vectorstores expose a method returning (doc, score)
                    pairs = vs.similarity_search_with_relevance_scores(query, k=k)
                    for doc, _score in pairs:
                        results.append(doc)
                except Exception:
                    # If the vectorstore doesn't support these methods, skip it
                    continue

        # Deduplicate by id_key while preserving order
        seen = set()
        deduped = []
        for d in results:
            meta = getattr(d, "metadata", {}) or {}
            doc_id = meta.get(self.id_key) or meta.get("id") or getattr(d, "id", None)
            if doc_id is None:
                # fallback: hash the content
                doc_id = hash(getattr(d, "page_content", getattr(d, "content", "")))
            if doc_id in seen:
                continue
            seen.add(doc_id)
            deduped.append(d)

        return deduped[:k]


# Instantiate lightweight retriever
retriever = MultiCollectionRetriever([text_vs, table_vs, image_vs], byte_store=byte_store)


def retrieve(query, k=6):
    """Return top-k relevant documents for a text query.

    Note: for image-based queries you would generate an image caption first and pass it
    as the query text.
    """
    docs = retriever.get_relevant_documents(query, k=k)
    return docs[:k]