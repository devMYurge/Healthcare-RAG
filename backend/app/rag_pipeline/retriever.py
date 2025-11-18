# rag_pipeline/retriever.py
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryByteStore
from langchain.docstore.document import Document
from langchain_community.vectorstores import Chroma

# Wrap Chroma collections with LangChain VectorStore interfaces
text_vs = Chroma(collection_name="text_docs", persist_directory="chroma_db")
image_vs = Chroma(collection_name="image_docs", persist_directory="chroma_db")
table_vs = Chroma(collection_name="table_docs", persist_directory="chroma_db")

# Byte store for parent docs
byte_store = InMemoryByteStore()

retriever = MultiVectorRetriever(
    vectorstores=[text_vs, table_vs, image_vs],
    byte_store=byte_store,
    id_key="doc_id",
)

def retrieve(query, k=6):
    # Use text embeddings on the query; for image queries, add an image-to-text caption first
    docs = retriever.get_relevant_documents(query)
    # Optional: rerank with cross-encoder
    return docs[:k]