# Healthcare RAG - AI-Powered Medical Information System

An intelligent healthcare information retrieval system built with **Retrieval-Augmented Generation (RAG)** technology. This application combines a powerful FastAPI backend with a modern React frontend to provide accurate, evidence-based medical information.

![Healthcare RAG](https://img.shields.io/badge/AI-Healthcare-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![React](https://img.shields.io/badge/React-18+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal)

## 🌟 Features

- **🤖 AI-Powered Responses**: Uses RAG technology to retrieve and synthesize medical information
- **🔍 Semantic Search**: Advanced vector search using ChromaDB and sentence transformers
- **📚 Evidence-Based**: All responses are backed by source documents with relevance scores
- **💬 Interactive Chat Interface**: User-friendly chat UI for natural conversations
- **⚡ Real-Time Processing**: Fast query processing and response generation
- **📊 System Statistics**: Monitor document count and system health
- **🎨 Modern UI**: Beautiful, responsive design with smooth animations

## 🏗️ Architecture

```
Healthcare-RAG/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # API endpoints
│   │   └── rag_impl.py   # RAG implementation (migrated from rag_system.py)
│   ├── data/               # Vector database storage
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API services
│   │   └── App.jsx         # Main app component
│   └── package.json        # Node dependencies
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Node.js 16 or higher
- npm or yarn

### Backend Setup (centralized Python environment)

This repository uses a centralized Python virtual environment at the project root (`.venv`) and a single `requirements.txt` for Python dependencies.

Recommended (one-step) setup


1. Make the helper script executable and run it from the repo root. The script will create `.venv`, install `requirements.txt`, and run a quick import verification:

```bash
chmod +x ./scripts/setup_env.sh
./scripts/setup_env.sh
```

If you prefer a faster install that skips the import verification step, run:

```bash
./scripts/setup_env.sh --no-verify
```

Manual setup (alternative)

1. Create and activate the venv:
```bash
python3 -m venv ./.venv
source ./.venv/bin/activate
```

2. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. (Optional) Create environment file:
```bash
cp backend/.env.example backend/.env
# Edit backend/.env if you want to customize settings
```

4. Start the backend server (from repo root):
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`.

Verify the environment

After installing, you can run a quick import verification script which reports missing or failing imports:

```bash
python3 scripts/verify_env.py
```

Exit code 0 indicates all checked modules imported successfully; non-zero indicates issues to fix.

### Development environment (canonical)

We recommend using the centralized virtualenv at the repo root (`.venv`) for
local development and CI. Quick summary:

- Create & activate (zsh):

  ```bash
  python3 -m venv ./.venv
  source ./.venv/bin/activate
  ```

- Install pinned dependencies and verify imports:

  ```bash
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt
  python3 scripts/verify_env.py
  ```

- Notes:
  - We pin several packages for reproducibility (example pins in `requirements.txt`: `pydantic==2.12.4`, `PyMuPDF==1.26.6`, `langchain==1.0.5`).
  - You may see a NumPy ABI warning when mixing extensions compiled against
    different NumPy major versions. If you encounter crashes, either pin
    `numpy<2` or rebuild the affected native extensions. If you plan to use
    `opencv-python`, note that some OpenCV releases expect `numpy>=2`.
  - To produce an exact lock file for CI, run:

    ```bash
    ./.venv/bin/pip freeze > requirements.lock
    ```


### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Create environment file** (optional):
   ```bash
   cp .env.example .env
   # Edit .env if backend is running on a different URL
   ```

4. **Start the development server**:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

## 📖 Usage

### Using the Web Interface

1. Open your browser to `http://localhost:3000`
2. Type your healthcare question in the chat input
3. Press Enter or click the send button
4. View the AI-generated response with sources and confidence scores
5. Click on suggested questions to get started quickly

### Example Questions

- "What is hypertension and how is it treated?"
- "Tell me about Type 2 diabetes management"
- "What are the symptoms of asthma?"
- "How is depression treated?"
- "What medications are used for GERD?"

### API Endpoints

The backend provides the following REST API endpoints:

#### Health Check
```bash
GET /api/health
```
Returns the health status of the system.

#### Query Healthcare Information
```bash
POST /api/query
Content-Type: application/json

{
  "question": "What is hypertension?",
  "max_results": 3
}
```

#### Add Document
```bash
POST /api/documents
Content-Type: application/json

{
  "content": "Document content here...",
  "metadata": {
    "category": "cardiovascular",
    "condition": "hypertension"
  }
}

#### Upload Image

POST an image file (multipart/form-data) to add an image document. Example using curl:

```bash
curl -X POST "http://localhost:8000/api/documents/image" \
  -F "file=@/path/to/example.jpg" \
  -F 'metadata={"source":"test","patient_id":"1234"};type=application/json'
```

Response includes the created document id and the upserted internal ids.
```

#### Get Statistics
```bash
GET /api/stats
```
Returns system statistics including document count and model information.

---

API notes — reranker & multimodal
--------------------------------

The `/api/query` endpoint accepts JSON body `{ "question": "...", "max_results": 3 }` and an optional query parameter `rerank` (default `true`) to enable/disable cross-encoder reranking. Example:

```bash
curl -X POST "http://localhost:8000/api/query?rerank=true" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is hypertension?","max_results":3}'
```

Multimodal queries (image + text) are supported via `/api/query/multimodal` which accepts `multipart/form-data` with fields `question` (form field) and optional `file` (image). Example:

```bash
curl -X POST "http://localhost:8000/api/query/multimodal?rerank=true" \
  -F "question=What is this skin lesion?" \
  -F "file=@/path/to/image.jpg"
```

Telemetry
---------
If environment variable `ENABLE_TELEMETRY=true` the server will write a `backend/data/telemetry.log` file containing per-query reranker/fusion summaries. Responses will also include a `telemetry` summary when enabled.


## 🔧 Configuration

### Backend Configuration

Edit `backend/.env` to customize:

```env
# OpenAI API Key (optional, for advanced LLM features)
OPENAI_API_KEY=your_api_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Database Configuration
CHROMA_PERSIST_DIR=./backend/data/chroma

# Model Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Internet fallback (optional)
USE_INTERNET=false

# Model routing / multimodal configuration (optional)
# - MODEL_DEPLOY_TYPE: "small" or "heavy". When "small" prefer lightweight LLMs for CPU/cloud deployment;
#   when "heavy" prefer larger local/GPU models.
# - LLM_MODEL: HuggingFace model id to use for generation (e.g. "mistralai/mistral-7b-v0.1" or "meta-llama/Llama-3-8b").
# - IMAGE_EMBED_MODEL: Optional SentenceTransformers model id for image embeddings (if set, used during image ingestion).
# - USE_GPU: "true"/"false" to hint ModelManager to attempt GPU-backed model loading.
# Example:
# MODEL_DEPLOY_TYPE=small
# LLM_MODEL=mistralai/mistral-7b-v0.1
# IMAGE_EMBED_MODEL=clip-ViT-B-32
# USE_GPU=false
```

### Frontend Configuration

Edit `frontend/.env` to customize:

```env
VITE_API_URL=http://localhost:8000
```

## 🔬 Model & Environment Mapping

The table below maps the models used by the RAG system to the environment variables that control them and the primary files where they are loaded or referenced. Paste this into your README or docs where helpful.

| Model / Config | Env var | Default / Example | Purpose | Primary file(s) |
|---|---:|---|---|---|
| Text embedding model | EMBEDDING_MODEL | all-MiniLM-L6-v2 | SentenceTransformers model used to embed all text (documents, dataset rows, fallback for images) | `backend/app/rag_impl.py`, `backend/app/model_manager.py` |
| LLM (text generator) | LLM_MODEL | (none) — set to HF model id to enable | HF text-generation pipeline used by ModelManager for answer generation; optional fallback used when unset | `backend/app/model_manager.py` |
| Image embedding model | IMAGE_EMBED_MODEL | (none) — set to CLIP-like model id to enable | Optional SentenceTransformer image embedder used to create image embeddings | `backend/app/model_manager.py`, `backend/app/rag_impl.py` |
| Model deployment preference | MODEL_DEPLOY_TYPE | small | Hint for routing/selection logic in ModelManager (e.g., small vs heavy) | `backend/app/model_manager.py` |
| Use GPU for HF pipelines | USE_GPU | false | If true and HF models available, pipeline device is set to GPU | `backend/app/model_manager.py` |
| Chroma persistent path | CHROMA_PERSIST_DIR | ./backend/data/chroma | Where ChromaDB stores vectors on disk | `backend/app/rag_impl.py` |
| Allow internet fallback | USE_INTERNET | false | If true, `HealthcareRAG._search_internet()` is used when local results are empty | `backend/app/rag_impl.py` |
| Returned model name (API) | (none) — added to response | N/A | `/api/query` responses include `model` field indicating LLM name or embedding model used | `backend/app/main.py`, `backend/app/rag_impl.py` |

If you prefer CSV format for documentation or automation, use the following CSV content and save it as `docs/model_mapping.csv` in your repo:

```
Model/Config,Env var,Default/Example,Purpose,Primary file(s)
Text embedding model,EMBEDDING_MODEL,all-MiniLM-L6-v2,"SentenceTransformers model used to embed text; fallback for other embeddings","backend/app/rag_impl.py; backend/app/model_manager.py"
LLM (text generator),LLM_MODEL,(none),"HuggingFace text-generation pipeline used by ModelManager; optional","backend/app/model_manager.py"
Image embedding model,IMAGE_EMBED_MODEL,(none),"Optional SentenceTransformers image embedder for image embeddings","backend/app/model_manager.py; backend/app/rag_impl.py"
Model deployment preference,MODEL_DEPLOY_TYPE,small,"Hint used when selecting light vs heavy models","backend/app/model_manager.py"
Use GPU for HF pipelines,USE_GPU,false,"Controls HF pipeline device selection","backend/app/model_manager.py"
Chroma persistent path,CHROMA_PERSIST_DIR,./backend/data/chroma,"ChromaDB persistence directory","backend/app/rag_impl.py"
Allow internet fallback,USE_INTERNET,false,"Enables web lookup fallback when no local docs found","backend/app/rag_impl.py"
Returned model name (API),(none),N/A,"/api/query returns 'model' field with model used (LLM or embedding model)","backend/app/main.py; backend/app/rag_impl.py"
```

## 🧪 Testing the Application

### Test Backend API

```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test query endpoint
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is diabetes?"}'
```

### Test Frontend

1. Open `http://localhost:3000` in your browser
2. Check that the system statistics panel shows the correct document count
3. Try asking different healthcare questions
4. Verify that sources and confidence scores are displayed

## 📦 Production Deployment

### Using Docker (Recommended)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - HOST=0.0.0.0
      - PORT=8000
    volumes:
      - ./backend/data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
```

Then run:
```bash
docker-compose up -d
```

### Manual Deployment

#### Backend
```bash
cd backend
pip install -r requirements.txt
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Frontend
```bash
cd frontend
npm install
npm run build
# Serve the dist/ folder with a web server like nginx
```

## 🛠️ Technologies Used

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **ChromaDB**: Vector database for semantic search
- **Sentence Transformers**: State-of-the-art text embeddings
- **LangChain**: Framework for LLM applications

LangChain compatibility note
---------------------------
This project includes small compatibility fallbacks to support different
LangChain layouts (for example `langchain`, `langchain_classic`, and
`langchain_core`). If you are running into import errors referencing
`langchain.retrievers`, `langchain.storage`, or `langchain.docstore`, you
have two options:

- Preferred (robust): keep the code as-is — the repository implements
  fallbacks and a small local retriever that works with common LangChain
  vectorstores (Chroma). No further action required.
- Alternative (reproducible): install the compatibility helper package
  `langchain-classic` which provides older LangChain module layouts and
  will make older import paths available. To add it to your environment:

```bash
# from the repo root, using the canonical venv
source ./.venv/bin/activate
pip install langchain-classic
```

We also added `langchain-classic` to `requirements.txt` as an optional
compatibility package. Pining to a single LangChain distribution is a
valid approach; if you prefer that, tell me and I will pin a specific
package+version and update the Quickstart accordingly.
- **Uvicorn**: ASGI server for production

### Frontend
- **React**: UI library for building interactive interfaces
- **Vite**: Fast build tool and dev server
- **Axios**: HTTP client for API requests
- **React Markdown**: Markdown rendering for formatted responses

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This application is for educational and informational purposes only. It should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.

## 🙏 Acknowledgments

- Medical knowledge base derived from publicly available healthcare information
- Built with modern AI and web technologies
- Powered by open-source sentence transformer models

## 📧 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

Made with ❤️ for better healthcare information access