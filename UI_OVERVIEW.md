# Healthcare RAG - User Interface Overview

## Application Screenshots & Features

### Main Interface

The Healthcare RAG application features a modern, user-friendly interface with the following components:

#### 1. Header Section
```
┌─────────────────────────────────────────────────────────┐
│  🏥 Healthcare RAG                                       │
│  AI-Powered Medical Information Retrieval               │
└─────────────────────────────────────────────────────────┘
```
- Logo and branding
- Application title
- Tagline

#### 2. Main Content Area

**Left Side - Chat Interface:**
```
┌─────────────────────────────────────────────────────────┐
│  💬 Chat Messages                                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 🤖  Hello! I'm your Healthcare AI assistant...   │  │
│  │     [Welcome message]                             │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 👤  What is hypertension?                        │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 🤖  Based on the available healthcare info...    │  │
│  │     [AI Response with sources]                    │  │
│  │     📚 Sources: [Document references]            │  │
│  │     Confidence: 95%                               │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  [Ask a healthcare question...]         📤       │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

Features:
- **Interactive Chat**: Message-based interface similar to ChatGPT
- **AI Responses**: Detailed answers with proper formatting
- **Source Citations**: Each response includes source documents
- **Confidence Scores**: Visual confidence indicators
- **Suggested Questions**: Quick-start buttons for common queries
- **Smooth Animations**: Messages slide in smoothly
- **Typing Indicator**: Shows when AI is processing

**Right Side - Information Panels:**

**Stats Panel:**
```
┌────────────────────────────┐
│ System Statistics          │
├────────────────────────────┤
│  ┌──────┐    ┌──────┐     │
│  │  10  │    │  🟢  │     │
│  │ Docs │    │Status│     │
│  └──────┘    └──────┘     │
│                            │
│ Model: all-MiniLM-L6-v2    │
└────────────────────────────┘
```

**Info Panel:**
```
┌────────────────────────────┐
│ About Healthcare RAG       │
├────────────────────────────┤
│ AI-powered system using    │
│ RAG to provide accurate    │
│ healthcare information...  │
│                            │
│ Features:                  │
│ 🔍 Semantic Search        │
│ 🤖 AI-Powered Responses   │
│ 📚 Evidence-Based         │
│ ⚡ Real-Time Results      │
└────────────────────────────┘
```

### Color Scheme

- **Primary**: Purple gradient (#667eea to #764ba2)
- **Background**: White cards with subtle shadows
- **User Messages**: Purple (#667eea)
- **AI Messages**: White with gray borders
- **Accents**: Teal for links and highlights

### Responsive Design

The interface adapts to different screen sizes:

#### Desktop (1200px+)
- Two-column layout (chat + sidebar)
- Full feature visibility
- Optimal reading experience

#### Tablet (768px - 1199px)
- Single column layout
- Stats panel moved to top
- Adjusted spacing

#### Mobile (< 768px)
- Single column, vertical stack
- Simplified navigation
- Touch-optimized buttons

### Interactive Elements

#### 1. Suggested Questions (First Visit)
```
┌──────────────────────────────────────────────────────┐
│ Try asking:                                          │
│ ┌────────────────────┐  ┌────────────────────────┐ │
│ │ What is            │  │ Tell me about         │ │
│ │ hypertension...    │  │ Type 2 diabetes...    │ │
│ └────────────────────┘  └────────────────────────┘ │
│ ┌────────────────────┐  ┌────────────────────────┐ │
│ │ What are symptoms  │  │ How is depression     │ │
│ │ of asthma?         │  │ treated?              │ │
│ └────────────────────┘  └────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

#### 2. Message Sources
Each AI response shows source documents:
```
📚 Sources:
┌─────────────────────────────────────────────────┐
│ Hypertension, also known as high blood...      │
│ Condition: hypertension | Category: cardiovasc │
│ Relevance: 95%                                  │
└─────────────────────────────────────────────────┘
```

#### 3. Confidence Bar
Visual indicator of response confidence:
```
Confidence: 95%
[████████████████████████████░░] 95%
```

#### 4. Loading State
When processing:
```
🤖  ● ● ●  (animated dots)
```

### User Experience Flow

1. **Landing**: User sees welcome message and suggested questions
2. **Query**: User types or clicks a suggestion
3. **Processing**: Typing indicator appears
4. **Response**: AI answer slides in with sources
5. **Follow-up**: User can continue conversation

### Accessibility Features

- High contrast text
- Keyboard navigation support
- Screen reader friendly
- Responsive touch targets
- Clear visual hierarchy

### Technical Features Visible to Users

1. **Real-time Updates**: Stats panel updates with system info
2. **Health Status**: Green indicator shows system is operational
3. **Document Count**: Shows how many documents in knowledge base
4. **Model Info**: Displays which AI model is being used
5. **Relevance Scores**: Transparency in source matching

### Error States

If backend is unavailable:
```
┌────────────────────────────────────────┐
│  ⚠️ Backend Connection Error          │
│                                        │
│  Could not connect to the backend API │
│  Please ensure the backend server     │
│  is running.                           │
│                                        │
│  cd backend && uvicorn app.main:app   │
│  --reload                              │
└────────────────────────────────────────┘
```

### Animation Details

- **Message Entry**: Slide up + fade in (0.3s)
- **Hover Effects**: Buttons lift with shadow
- **Typing Indicator**: Bouncing dots animation
- **Confidence Bar**: Smooth width transition (0.5s)
- **Suggestions**: Scale up on hover

## API Visualization

The backend provides these endpoints accessible via the frontend:

```
GET  /api/health       → System health check
GET  /api/stats        → Knowledge base statistics  
POST /api/query        → Ask healthcare questions
POST /api/documents    → Add new documents
GET  /docs             → Interactive API documentation
```

All communication happens through Axios with proper error handling and loading states.
