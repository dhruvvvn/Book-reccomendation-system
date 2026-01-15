# Personalized Book Recommendation Assistant - Backend

A FastAPI backend implementing the **Retrieve & Rerank** architecture for personalized book recommendations.

## Architecture

```
User Query → Embedding → Vector Search (FAISS) → Candidate Retrieval
                                                        ↓
                              Final Recommendations ← LLM Reranking (Gemini)
```

### Quick Start (Windows)
    
1.  **Setup Environment**
    Double-click `setup.bat`. This will:
    - Create a virtual environment
    - Install all dependencies
    - Create your `.env` file from `.env.example`
    
2.  **Configure API Key**
    Open the newly created `.env` file in a text editor and add your `GEMINI_API_KEY`.
    
3.  **Ingest Data**
    Double-click `ingest.bat`. This will:
    - Load the sample books from `data/books_sample.json`
    - Generate embeddings and create the FAISS index
    
4.  **Run Server**
    Double-click `run.bat`. This will start the server at `http://localhost:8000`.
    
    Visit `http://localhost:8000/docs` for the API documentation.

## Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/   # API route handlers
│   ├── models/             # Pydantic schemas
│   ├── services/           # Business logic (embedding, retrieval, reranking)
│   ├── db/                 # Database connections (FAISS, PostgreSQL)
│   └── utils/              # Helper functions
├── scripts/
│   └── ingest_data.py      # Data ingestion script
├── data/
│   └── books_sample.json   # Sample dataset
└── requirements.txt
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/chat` | Get personalized recommendations |
| GET | `/api/v1/books/search` | Semantic book search |
| GET | `/api/v1/books/{id}` | Get book details |

## Key Features

- **Hybrid Retrieval**: Combines vector similarity with metadata filtering
- **LLM Reranking**: Uses Gemini Pro for context-aware ranking
- **Async Everything**: Full async/await support
- **Caching**: TTL-based caching for repeated queries
- **Modular Design**: Clean separation of concerns
