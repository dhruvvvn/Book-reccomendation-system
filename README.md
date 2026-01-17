# 📚 BookAI - Intelligent Book Recommendation System

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![React](https://img.shields.io/badge/react-18.0-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95-green.svg)
![Tailwind](https://img.shields.io/badge/Tailwind-3.0-blue.svg)

**BookAI** is a next-generation book recommendation engine that combines **semantic vector search** with a **conversational AI personality**. Unlike traditional keyword search, it understands the *mood* and *meaning* of your request.

> "A librarian that actually listens, checks the back room (Google Books), and adapts to your personality."

---

## ✨ Key Features

- **🤖 Conversational Librarian**: Choose your assistant's personality (Friendly, Professional, Sarcastic, Flirty, Mentor).
- **🧠 Hybrid Search Architecture**:
    - **Vector Search (FAISS)**: Finds books by semantic meaning ("scary", "uplifting").
    - **SQL Fallback**: robust keyword matching.
    - **JIT (Just-In-Time) Discovery**: Fetches books from Google Books API if they aren't in your local database.
- **⚡ RAG (Retrieval-Augmented Generation)**: Uses Gemini LLM to generate personalized, hallucination-free explanations.
- **🎨 Glassmorphism UI**: Modern React frontend with smooth framer-motion animations.
- **🌓 Dark/Light Mode**: Fully themable interface.

---

## 🛠️ Technology Stack

### Backend
- **Python 3.11**
- **FastAPI** (High-performance API)
- **FAISS** (Vector Similarity Search)
- **Sentence-Transformers** (Embeddings)
- **Google Gemini 1.5** (LLM Intelligence)
- **SQLite** (Local Database)

### Frontend
- **React + Vite**
- **Tailwind CSS** (Styling)
- **Framer Motion** (Animations)
- **Axios** (API Communication)

---

## 🚀 Installation & Setup

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- Google Gemini API Key (Get one [here](https://aistudio.google.com/))

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Frontend Setup

```bash
cd frontend-react

# Install dependencies
npm install

# Configure environment
# (Optional: Create .env if you need to change API URL)
```

---

## ▶️ Running the App

You can run the entire system with the provided script (Windows):

```bash
# In the root directory
./run_all.bat
```

Or manually:

**Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend-react
npm run dev
```

Open your browser to `http://localhost:3000`.

---

## 📸 Usage Guide

1.  **Browse**: Explore trending books on the home page.
2.  **Search**: Use the search bar for specific titles.
3.  **Chat**: Click the chat bubble to talk to the AI.
    - *Try: "I want a book that feels like a rainy day."*
    - *Try: "Do you have Atomic Habits?"* (Triggers JIT search)
4.  **Settings**: Change the AI persona in the Settings menu.

---

## 📂 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints (Chat, Auth, Discover)
│   │   ├── services/     # Logic (Retrieval, Reranking, Embedding)
│   │   └── models/       # Pydantic Schemas
│   └── data/             # SQLite DB and FAISS index
│
└── frontend-react/
    ├── src/
    │   ├── components/   # ChatWidget, BookCard, NavBar
    │   ├── pages/        # Home, Settings, ReadingList
    │   └── context/      # UserContext
```

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
