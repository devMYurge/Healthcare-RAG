# API Testing Guide

This guide shows how to test the Healthcare RAG API endpoints.

## Prerequisites

- Backend server running on http://localhost:8000
- curl or any HTTP client installed

## Test Endpoints

### 1. Health Check

Check if the backend is running:

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "rag_initialized": true
}
```

### 2. Get System Statistics

Get information about the knowledge base:

```bash
curl http://localhost:8000/api/stats
```

Expected response:
```json
{
  "document_count": 10,
  "collection_name": "healthcare_documents",
  "embedding_model": "all-MiniLM-L6-v2",
  "status": "active"
}
```

### 3. Query Healthcare Information

Ask a question about healthcare:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is hypertension?",
    "max_results": 3
  }'
```

Expected response:
```json
{
  "answer": "Based on the available healthcare information:\n\nHypertension, also known as high blood pressure...",
  "sources": [
    {
      "content": "Hypertension, also known as high blood pressure...",
      "metadata": {
        "category": "cardiovascular",
        "condition": "hypertension"
      },
      "relevance_score": 0.95
    }
  ],
  "confidence": 0.95
}
```

### 4. Add a Document

Add a new document to the knowledge base:

```bash
curl -X POST http://localhost:8000/api/documents \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Pneumonia is an infection that inflames air sacs in lungs. Treatment includes antibiotics, rest, and fluids.",
    "metadata": {
      "category": "respiratory",
      "condition": "pneumonia"
    }
  }'
```

Expected response:
```json
{
  "message": "Document added successfully",
  "document_id": "doc_12345678"
}
```

## Testing with Python

You can also test using Python:

```python
import requests

# Health check
response = requests.get("http://localhost:8000/api/health")
print(response.json())

# Query
query_data = {
    "question": "What is diabetes?",
    "max_results": 3
}
response = requests.post("http://localhost:8000/api/query", json=query_data)
print(response.json())
```

## Testing with JavaScript/Node.js

```javascript
// Using fetch
async function testAPI() {
  // Health check
  const health = await fetch('http://localhost:8000/api/health');
  console.log(await health.json());
  
  // Query
  const query = await fetch('http://localhost:8000/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: 'What is asthma?',
      max_results: 3
    })
  });
  console.log(await query.json());
}

testAPI();
```

## Interactive API Documentation

The backend provides interactive API documentation powered by Swagger UI:

1. Navigate to http://localhost:8000/docs
2. Try out endpoints directly from the browser
3. View request/response schemas
4. Test with different parameters

## Common Test Scenarios

### Test 1: Basic Query Flow
1. Check health endpoint
2. Get system stats
3. Submit a query
4. Verify response has answer, sources, and confidence

### Test 2: Document Management
1. Add a new document
2. Check stats to verify count increased
3. Query for the new document content
4. Verify the new document appears in sources

### Test 3: Multiple Queries
1. Submit several different queries
2. Compare confidence scores
3. Verify source relevance scores
4. Check response times

## Expected Behavior

### Success Cases
- Health endpoint returns 200 status
- Queries return relevant information
- Sources include metadata and scores
- Confidence scores are between 0 and 1

### Error Cases
- Invalid JSON returns 422 (Unprocessable Entity)
- Server errors return 500 (Internal Server Error)
- Missing required fields return validation errors

## Performance Testing

Test response times:

```bash
# Time a query
time curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is hypertension?"}'
```

Expected: < 2 seconds for most queries

## Troubleshooting

### Connection Refused
- Ensure backend is running
- Check if port 8000 is correct
- Verify firewall settings

### Slow Responses
- First query may be slower (model loading)
- Subsequent queries should be faster
- Check system resources

### Empty or Poor Results
- Verify documents are loaded
- Check question phrasing
- Review relevance scores
