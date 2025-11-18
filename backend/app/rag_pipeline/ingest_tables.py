# rag_pipeline/ingest_tables.py
import pandas as pd
import chromadb

client = chromadb.PersistentClient(path="chroma_db")
table_collection = client.get_or_create_collection("table_docs")

def row_to_text(row):
    return " | ".join([f"{k}: {row[k]}" for k in row.index])

def upsert_table(doc_id, csv_path, metadata):
    df = pd.read_csv(csv_path)
    rows_text = [row_to_text(df.iloc[i]) for i in range(len(df))]
    embeddings = embed_text(rows_text)
    ids = [f"{doc_id}_row_{i}" for i in range(len(df))]
    table_collection.upsert(ids=ids, embeddings=embeddings, metadatas=[metadata]*len(df), documents=rows_text)