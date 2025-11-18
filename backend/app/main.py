"""
Healthcare RAG API - Main Application
Provides endpoints for healthcare information retrieval using RAG.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import uuid
import json

from .rag_impl import HealthcareRAG

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
    model: Optional[str] = None
    reranked: Optional[bool] = None
    telemetry: Optional[dict] = None


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
async def query_healthcare_info(request: QueryRequest, rerank: bool = True):
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
            max_results=request.max_results,
            rerank=rerank
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


@app.post("/api/documents/image")
async def upload_image(file: UploadFile = File(...), metadata: Optional[str] = Form(None)):
    """
    Upload an image and add it to the image collection.

    Accepts a multipart/form-data image file and optional metadata (JSON string).
    """
    global rag_system

    if rag_system is None:
        try:
            rag_system = HealthcareRAG()
        except Exception as e:
            print(f"Failed to initialize RAG system: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to initialize RAG system.")

    # Ensure images dir exists
    images_dir = os.path.join(os.getcwd(), "backend", "data", "images")
    os.makedirs(images_dir, exist_ok=True)

    # Save uploaded file
    try:
        content = await file.read()
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        doc_id = f"img_{uuid.uuid4().hex[:8]}"
        save_path = os.path.join(images_dir, f"{doc_id}{ext}")
        with open(save_path, "wb") as f:
            f.write(content)
    except Exception as e:
        print(f"Failed to save uploaded image: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded image")

    # Parse metadata if provided
    meta_obj = None
    if metadata:
        try:
            meta_obj = json.loads(metadata)
        except Exception:
            meta_obj = {"raw": metadata}

    try:
        upsert_ids = rag_system.ingestor.upsert_image(doc_id, save_path, metadata=meta_obj)
        return {"message": "Image uploaded and ingested", "document_id": doc_id, "upsert_ids": upsert_ids}
    except Exception as e:
        print(f"Failed to ingest image: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest uploaded image")


@app.post("/api/query/multimodal", response_model=QueryResponse)
async def query_multimodal(file: UploadFile = File(None), question: Optional[str] = Form(None), max_results: int = Form(3), rerank: bool = Form(True)):
    """Multimodal query endpoint.

    Accepts an optional uploaded image plus a form field `question`. The image will be saved
    to `backend/data/images` and passed to the RAG system as an image path so a multimodal
    model (if configured) can be used.
    """
    global rag_system

    if rag_system is None:
        try:
            rag_system = HealthcareRAG()
        except Exception as e:
            print(f"Failed to initialize RAG system: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to initialize RAG system.")

    if not question:
        raise HTTPException(status_code=400, detail="Field 'question' is required.")

    images = None
    if file is not None:
        # Save uploaded image
        images_dir = os.path.join(os.getcwd(), "backend", "data", "images")
        os.makedirs(images_dir, exist_ok=True)
        try:
            content = await file.read()
            ext = os.path.splitext(file.filename)[1] or ".jpg"
            doc_id = f"qimg_{uuid.uuid4().hex[:8]}"
            save_path = os.path.join(images_dir, f"{doc_id}{ext}")
            with open(save_path, "wb") as f:
                f.write(content)
            images = [save_path]
        except Exception as e:
            print(f"Failed to save uploaded query image: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded image")

    try:
        result = rag_system.query(question=question, max_results=max_results, images=images, rerank=rerank)
        return QueryResponse(**result)
    except Exception as e:
        print(f"Multimodal query failed: {e}")
        raise HTTPException(status_code=500, detail="Multimodal query failed. Please try again.")


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
