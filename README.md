# Adaptive Reasoning Agent

An AI-powered chat application that adapts its reasoning depth based on network conditions. Built with FastAPI, React, and Mistral AI.

## Features

- 🧠 **Multi-Mode Reasoning**: Auto, Fast, Standard, and Deep reasoning modes
- 📄 **RAG Pipeline**: Upload and search documents for knowledge-augmented responses
- 💬 **Real-time Streaming**: WebSocket-based response streaming
- 🎤 **Voice Integration**: Speech-to-text input and text-to-speech output
- 📊 **Chat History**: Persistent conversation storage and retrieval
- 🌐 **Network-Aware**: Automatically adapts processing based on network conditions
- 📱 **Responsive Design**: Mobile-friendly UI with Tailwind CSS

## Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- Docker (for Qdrant vector database)
- Mistral AI API key

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/MUHAMMADSAAD12345/MCS.git
cd MCS
```

### 2. Set up Python environment

```bash
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# or
source .venv/bin/activate  # macOS/Linux

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..
```

### 3. Set up environment variables

Create a `.env` file in the `backend/` directory:

```env
MISTRAL_API_KEY=your_mistral_api_key_here
DATABASE_URL=sqlite:///./data/sessions.db
QDRANT_HOST=localhost
QDRANT_PORT=6333
SECRET_KEY=your-secret-key-change-this-in-production
```

### 4. Start Docker containers

```bash
# Start Qdrant vector database
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

### 5. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## Running the Project

### Option 1: Run both backend and frontend

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

The application will be available at `http://localhost:3000`

### Option 2: Production build

```bash
# Build frontend
cd frontend
npm run build
cd ..

# Backend runs with gunicorn (install if needed)
pip install gunicorn
cd backend
gunicorn main:app -w 4 -b 0.0.0.0:8000
```

## Project Structure

```
MCS/
├── backend/
│   ├── api/                 # API endpoints (auth, chat, documents)
│   ├── core/                # Core agent logic
│   ├── rag/                 # RAG pipeline (embeddings, retrieval, ingestion)
│   ├── services/            # Database and session management
│   ├── tools/               # Tool implementations (web search, datetime, etc.)
│   ├── auth/                # JWT and password handling
│   ├── config.py            # Configuration settings
│   ├── main.py              # FastAPI entry point
│   └── requirements.txt      # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks (WebSocket, voice, etc.)
│   │   ├── stores/          # Zustand state management
│   │   ├── types/           # TypeScript type definitions
│   │   ├── App.tsx          # Main app component
│   │   └── main.tsx         # Vite entry point
│   ├── index.html
│   ├── package.json
│   └── tsconfig.json
│
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info

### Chat
- `WS /api/chat/ws` - WebSocket for streaming responses
- `POST /api/chat/send` - Send message (REST fallback)
- `GET /api/chat/sessions` - List user's chat sessions
- `GET /api/chat/sessions/{id}/messages` - Load session messages

### Documents
- `POST /api/documents/upload` - Upload document
- `GET /api/documents/list` - List user's documents
- `DELETE /api/documents/{id}` - Delete document

### Network
- `GET /api/network/status` - Get current network tier and latency

## Configuration

### Reasoning Modes

- **Auto**: Automatically selects based on network conditions
- **Fast**: Quick responses (basic planning + response)
- **Standard**: Balanced (planning + research + synthesis)
- **Deep**: Thorough analysis (planning + research + synthesis + verification)

### Supported Document Formats

- PDF (.pdf)
- Word (.docx)
- Text (.txt)
- CSV (.csv)
- Markdown (.md)

## Technology Stack

**Backend:**
- FastAPI - Web framework
- Mistral AI - LLM provider
- Qdrant - Vector database for embeddings
- SQLite - Session/user storage
- python-jose - JWT handling
- Pydantic - Data validation

**Frontend:**
- React 18 - UI library
- TypeScript - Type safety
- Vite - Build tool
- Tailwind CSS - Styling
- Zustand - State management
- Lucide React - Icons
- react-markdown - Markdown rendering

## Troubleshooting

### Qdrant connection failed
```bash
# Make sure Qdrant is running
docker ps | grep qdrant

# If not running, start it
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

### Backend import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend won't connect to backend
- Check that backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify API token in localStorage

### MISTRAL_API_KEY not found
- Ensure `.env` file is in the `backend/` directory
- Restart backend after adding the API key

## Default Test Credentials

- Username: `demouser`
- Password: `password123`

(Create new accounts via the registration page)

## Performance Tips

- Use "Fast" mode for quick interactions
- Use "Deep" mode for complex reasoning tasks
- Upload documents to enable RAG for specific knowledge domains
- Monitor network latency in the UI header

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.

---

**Built with ❤️ for the Mistral AI Hackathon**
