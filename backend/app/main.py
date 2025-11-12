"""
Healthcare RAG API - Main Application
Provides endpoints for healthcare information retrieval using RAG.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

from .rag_system import HealthcareRAG

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Healthcare RAG API",
    description="AI-powered healthcare information retrieval system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system
rag_system = None


class QueryRequest(BaseModel):
    """Request model for healthcare queries"""
    question: str
    max_results: Optional[int] = 3


class QueryResponse(BaseModel):
    """Response model for healthcare queries"""
    answer: str
    sources: List[dict]
    confidence: Optional[float] = None


class DocumentRequest(BaseModel):
    """Request model for adding documents"""
    content: str
    metadata: Optional[dict] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize RAG system on startup"""
    global rag_system
    try:
        rag_system = HealthcareRAG()
        print("Healthcare RAG system initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize RAG system: {e}")
        print("RAG system will be initialized on first request")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Healthcare RAG API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/api/query",
            "add_document": "/api/documents",
            "health": "/api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "rag_initialized": rag_system is not None
    }


@app.post("/api/query", response_model=QueryResponse)
async def query_healthcare_info(request: QueryRequest):
    """
    Query the healthcare database using RAG
    
    Args:
        request: QueryRequest with question and optional max_results
        
    Returns:
        QueryResponse with answer, sources, and confidence
    """
    global rag_system
    
    # Initialize RAG system if not already done
    if rag_system is None:
        try:
            rag_system = HealthcareRAG()
        except Exception as e:
            # Log the error but don't expose details to user
            print(f"Failed to initialize RAG system: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize RAG system. Please check server logs."
            )
    
    try:
        result = rag_system.query(
            question=request.question,
            max_results=request.max_results
        )
        return QueryResponse(**result)
    except Exception as e:
        # Log the error but don't expose details to user
        print(f"Query failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Query processing failed. Please try again."
        )


@app.post("/api/documents")
async def add_document(request: DocumentRequest):
    """
    Add a document to the healthcare knowledge base
    
    Args:
        request: DocumentRequest with content and metadata
        
    Returns:
        Success message with document ID
    """
    global rag_system
    
    if rag_system is None:
        try:
            rag_system = HealthcareRAG()
        except Exception as e:
            # Log the error but don't expose details to user
            print(f"Failed to initialize RAG system: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize RAG system. Please check server logs."
            )
    
    try:
        doc_id = rag_system.add_document(
            content=request.content,
            metadata=request.metadata
        )
        return {
            "message": "Document added successfully",
            "document_id": doc_id
        }
    except Exception as e:
        # Log the error but don't expose details to user
        print(f"Failed to add document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to add document. Please try again."
        )


@app.get("/api/stats")
async def get_stats():
    """Get statistics about the knowledge base"""
    global rag_system
    
    if rag_system is None:
        return {"document_count": 0, "status": "not_initialized"}
    
    try:
        stats = rag_system.get_stats()
        return stats
    except Exception as e:
        # Log the error but don't expose details to user
        print(f"Failed to get stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve statistics. Please try again."
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
