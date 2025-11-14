# Quick Start Guide

## Getting Started with Healthcare RAG

This guide will help you get the Healthcare RAG application up and running in minutes.

### Option 1: Docker (Recommended)

The easiest way to run Healthcare RAG is using Docker:

```bash
# Clone the repository (if not already done)
git clone https://github.com/devMYurge/Healthcare-RAG.git
cd Healthcare-RAG

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

### Option 2: Automated Script

Use the provided startup script:

```bash
chmod +x start.sh
./start.sh
```

The script will:
1. Check for Docker and offer to use it
2. Set up Python virtual environment
3. Install all dependencies
4. Start both backend and frontend servers

### Option 3: Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Accessing the Application

Once started, open your browser and navigate to:

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Using the Application

1. **Ask Questions**: Type your healthcare-related questions in the chat interface
2. **View Sources**: See the evidence backing each response
3. **Check Confidence**: Review confidence scores for each answer
4. **Try Suggestions**: Click on suggested questions to get started

## Sample Questions

Try asking:
- "What is hypertension and how is it treated?"
- "Tell me about Type 2 diabetes management"
- "What are the symptoms of asthma?"
- "How is depression treated?"
- "What medications are used for GERD?"

## Troubleshooting

### Backend not starting
- Check if port 8000 is available
- Ensure all Python dependencies are installed
- Check logs for specific errors

### Frontend not connecting
- Verify backend is running at http://localhost:8000
- Check if port 3000 is available
- Clear browser cache and reload

### Dependencies failing to install
- Check your internet connection
- Try using Docker instead
- Update pip: `pip install --upgrade pip`

## Next Steps

- Add more healthcare documents via the API
- Customize the embedding model
- Deploy to production
- Integrate with your healthcare database

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Open an issue on GitHub
- Review API documentation at http://localhost:8000/docs
