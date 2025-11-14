# Healthcare RAG - Visual Preview

## Application Interface

Since we cannot run the application in this environment due to network restrictions, here's a detailed description of what the interface looks like when running:

### 1. Landing Page

When you first open http://localhost:3000, you see:

**Header:**
- Purple gradient background with white text
- Logo: 🏥 icon
- Title: "Healthcare RAG"
- Tagline: "AI-Powered Medical Information Retrieval"

**Main Area - Left Side (Chat Interface):**
- White background with rounded corners
- Welcome message from the AI assistant (🤖 icon)
- Four suggested question buttons in a grid:
  - "What is hypertension and how is it treated?"
  - "Tell me about Type 2 diabetes management"
  - "What are the symptoms of asthma?"
  - "How is depression treated?"
- Input box at the bottom with placeholder: "Ask a healthcare question..."
- Send button (📤) on the right

**Main Area - Right Side:**
- **Stats Panel** (white card):
  - Two metrics side by side:
    - Document count: "10" (large purple number)
    - Status: Green circle (🟢)
  - Model information: "all-MiniLM-L6-v2"

- **Info Panel** (white card):
  - Description of the RAG system
  - Four feature badges in a 2x2 grid:
    - 🔍 Semantic Search
    - 🤖 AI-Powered Responses
    - 📚 Evidence-Based
    - ⚡ Real-Time Results

### 2. During a Query

When user types "What is hypertension?" and presses send:

1. **User message appears:**
   - Right-aligned blue bubble
   - User icon (👤) on the right
   - Message text: "What is hypertension?"
   - Timestamp below

2. **Loading indicator:**
   - AI icon (🤖) on the left
   - Three animated bouncing dots

3. **AI Response appears:**
   - Left-aligned white bubble
   - AI icon (🤖) on the left
   - Detailed answer with formatted text
   - **Sources section** below (light gray background):
     - "📚 Sources:" header
     - List of source documents with:
       - Document excerpt
       - Condition tag (e.g., "Condition: hypertension")
       - Category tag (e.g., "Category: cardiovascular")
       - Relevance score badge (e.g., "Relevance: 95%" in green)
   - **Confidence bar:**
     - Label: "Confidence: 95%"
     - Purple gradient progress bar showing 95%
   - Timestamp below

### 3. Color Palette

```
Primary Background: Purple gradient (#667eea to #764ba2)
Cards: White (#ffffff) with subtle shadow
User Messages: Purple (#667eea)
AI Messages: White with gray border (#f8f9fa)
Text: Dark gray (#333333)
Secondary Text: Medium gray (#666666)
Success/Green: #27ae60
Badges: Light gray (#e9ecef)
Relevance Score: Light green (#d4edda)
```

### 4. Animations

- **Message entry**: Slides up and fades in smoothly (0.3s)
- **Suggestion hover**: Buttons lift up with shadow and turn purple
- **Typing indicator**: Dots bounce up and down in sequence
- **Confidence bar**: Fills from left to right smoothly (0.5s)
- **Send button hover**: Scales up slightly and darkens

### 5. Responsive Behavior

**Desktop (1200px+):**
```
┌─────────────────────────────────────────────────────┐
│                    Header                           │
├────────────────────────────┬────────────────────────┤
│                            │    Stats Panel         │
│       Chat Interface       │                        │
│                            │    Info Panel          │
│         (700px)            │     (350px)            │
└────────────────────────────┴────────────────────────┘
```

**Tablet (768-1199px):**
```
┌─────────────────────────────────────────────────────┐
│                    Header                           │
├─────────────────────────────────────────────────────┤
│              Stats Panel                            │
├─────────────────────────────────────────────────────┤
│              Info Panel                             │
├─────────────────────────────────────────────────────┤
│           Chat Interface                            │
│             (Full Width)                            │
└─────────────────────────────────────────────────────┘
```

**Mobile (<768px):**
```
┌────────────────────┐
│      Header        │
├────────────────────┤
│   Stats Panel      │
├────────────────────┤
│   Info Panel       │
├────────────────────┤
│  Chat Interface    │
│   (Full Width)     │
└────────────────────┘
```

### 6. Error State

If backend is not running:
```
┌─────────────────────────────────────────────────────┐
│                    Header                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│              ⚠️ Backend Connection Error            │
│                                                     │
│   Could not connect to the backend API.            │
│   Please ensure the backend server is running.     │
│                                                     │
│   cd backend && uvicorn app.main:app --reload      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 7. Backend API Documentation

When you visit http://localhost:8000/docs:

You see FastAPI's Swagger UI with:
- API title: "Healthcare RAG API"
- Version: "1.0.0"
- Description: "AI-powered healthcare information retrieval system"
- Expandable endpoint sections:
  - GET / - Root endpoint
  - GET /api/health - Health check
  - GET /api/stats - Get statistics
  - POST /api/query - Query healthcare info
  - POST /api/documents - Add document
- Interactive "Try it out" buttons for each endpoint
- Request/response schema documentation

### 8. Sample Interaction Flow

**User:** Types "What is diabetes?"

**System:** Shows typing indicator (3 bouncing dots)

**AI Response:**
```
Based on the available healthcare information:

Type 2 diabetes is a chronic condition affecting how the body 
processes blood sugar (glucose). Symptoms include increased 
thirst, frequent urination, and fatigue. Management involves 
blood sugar monitoring, healthy eating, regular exercise, and 
medications like metformin or insulin if needed.

Related conditions: diabetes

📚 Sources:
┌────────────────────────────────────────────────────┐
│ Type 2 diabetes is a chronic condition affecting  │
│ how the body processes blood sugar (glucose)...   │
│                                                    │
│ Condition: diabetes | Category: endocrine         │
│ Relevance: 98%                                     │
└────────────────────────────────────────────────────┘

Confidence: 98%
[███████████████████████████████████████░░] 98%

12:34:56 PM
```

## How to See It Yourself

To see the actual running application:

1. **Start the backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Open in browser:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

Or use Docker:
```bash
docker-compose up
```

Then take screenshots to share with your team!

## Design Inspiration

The interface is inspired by:
- Modern chat applications (clean, conversational)
- Medical software (professional, trustworthy)
- AI assistants (helpful, intelligent)
- Material Design (cards, shadows, elevation)

The purple gradient gives it a tech-forward feel while maintaining medical professionalism.
