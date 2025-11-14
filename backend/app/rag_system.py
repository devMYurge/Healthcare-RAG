"""
Healthcare RAG System Implementation
Handles document retrieval and answer generation for healthcare queries.
"""

import os
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np


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
        self.embedding_model_name = embedding_model
        
        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./backend/data/chroma"
        ))
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"Loaded existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Healthcare documents and knowledge base"}
            )
            print(f"Created new collection: {collection_name}")
            # Add sample healthcare data
            self._add_sample_data()
    
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
            self.add_document(doc["content"], doc["metadata"])
        print(f"Added {len(sample_documents)} sample documents to knowledge base")
    
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
        # Generate query embedding
        query_embedding = self.embedding_model.encode(question).tolist()
        
        # Search for relevant documents
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max_results
        )
        
        # Extract results
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []
        
        if not documents:
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
