# DocRAG — Open-Source Document RAG System

A production-ready **Retrieval-Augmented Generation** system for document retrieval and Q&A.

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | Next.js API Routes + FastAPI (Python) |
| Database | Neon Postgres + pgvector |
| RAG Framework | LlamaIndex |
| Embeddings | BAAI/bge-small-en-v1.5 (384-dim) |
| LLM | Mistral / Llama 3.1 / Qwen 2.5 via Ollama |
| Parsing | pdfplumber, pytesseract, camelot-py |
| Storage | Vercel Blob / local filesystem |
| CI/CD | GitHub Actions → Vercel |

---

## Architecture

```
User uploads PDF
 → Next.js API receives file
 → File stored in Vercel Blob (or local)
 → Ingestion API (FastAPI) parses document
    → PDF text extraction (pdfplumber / pypdf)
    → OCR for scanned pages (pytesseract)
    → Layout analysis → Markdown
    → Table / form extraction (camelot / pdfplumber)
 → Chunking via LlamaIndex SentenceSplitter
 → Embedding generation (bge-small-en-v1.5)
 → Chunks + embeddings stored in Neon Postgres (pgvector)

User asks question
 → Query embedding generated
 → pgvector similarity search (top_k=8)
 → LlamaIndex retriever fetches matching chunks
 → Open-source LLM generates answer with citations
 → Answer returned with source chunks + page numbers
```

---

## Project Structure

```
├── apps/web/                   # Next.js 15 frontend
│   ├── app/
│   │   ├── page.tsx            # Home — document list
│   │   ├── upload/page.tsx     # Upload page
│   │   ├── chat/page.tsx       # Chat interface
│   │   ├── api/upload/route.ts # Upload API
│   │   ├── api/chat/route.ts   # Chat API
│   │   ├── api/documents/route.ts
│   │   └── api/health/route.ts
│   └── lib/
│       ├── db.ts               # Prisma client
│       ├── rag.ts              # RAG service calls
│       └── storage.ts          # File storage
│
├── services/ingestion/         # FastAPI ingestion worker
│   ├── main.py                 # FastAPI app
│   ├── ingest.py               # Orchestrator
│   ├── parsers/
│   │   ├── pdf_parser.py       # PDF text extraction
│   │   ├── ocr_parser.py       # OCR (pytesseract)
│   │   ├── layout_parser.py    # Layout → Markdown
│   │   └── form_parser.py      # Table / form extraction
│   ├── rag/
│   │   ├── indexer.py          # LlamaIndex chunking + embedding
│   │   └── retriever.py        # Vector search + LLM answer
│   └── tests/
│       └── test_parsers.py
│
├── prisma/
│   └── schema.prisma           # Database schema
│
├── .github/workflows/
│   ├── ci.yml                  # PR checks
│   └── deploy.yml              # Deploy to Vercel
│
├── vercel.json
├── .env.example
└── README.md
```

---

## Local Setup

### Prerequisites

- Node.js ≥ 20
- Python ≥ 3.11
- PostgreSQL with pgvector (or a Neon account)
- Ollama (for local LLM inference)

### 1. Clone & configure

```bash
git clone <your-repo-url>
cd Rag_pipeline-1
cp .env.example .env
# Edit .env with your Neon database URL and other settings
```

### 2. Setup the database

```bash
cd apps/web
npm install
npx prisma generate
npx prisma db push   # Creates tables in your Neon Postgres
```

Enable pgvector in your Neon database (if not already):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Start the Next.js app

```bash
cd apps/web
npm run dev
# → http://localhost:3000
```

### 4. Start the ingestion service

```bash
cd services/ingestion
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

### 5. Start Ollama

```bash
ollama pull mistral
ollama serve
# → http://localhost:11434
```

---

## Neon Postgres Setup

1. Create a project at [neon.tech](https://neon.tech)
2. Copy the connection string from the dashboard
3. Set `DATABASE_URL` and `DIRECT_URL` in your `.env`
4. Enable pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
5. Run migrations:
   ```bash
   cd apps/web && npx prisma db push
   ```

---

## Vercel Deployment

### 1. Connect to Vercel

```bash
npm i -g vercel
vercel link
```

### 2. Add Neon from Vercel Marketplace

1. Go to your Vercel project → **Storage** tab
2. Click **Connect Database** → choose **Neon Postgres**
3. The `DATABASE_URL` environment variable is set automatically

### 3. Set environment variables

In Vercel project settings → Environment Variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Auto-set by Neon integration |
| `DIRECT_URL` | Neon direct connection URL |
| `BLOB_READ_WRITE_TOKEN` | Vercel Blob token |
| `INGESTION_API_URL` | URL of your FastAPI service |
| `OLLAMA_BASE_URL` | Ollama endpoint |
| `LLM_MODEL` | e.g. `mistral` |
| `EMBED_MODEL` | e.g. `BAAI/bge-small-en-v1.5` |

### 4. Deploy

```bash
vercel --prod
```

Or push to `main` and the GitHub Actions deploy workflow runs automatically.

---

## Ingestion Service Deployment

The FastAPI ingestion service handles heavy document parsing (OCR, layout analysis)
and should **not** run inside Vercel serverless functions. Deploy it separately:

**Option A — Railway / Render / Fly.io**

```bash
# From services/ingestion/
# Use their CLI or connect your GitHub repo
```

**Option B — Docker**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Environment Variables

See [.env.example](.env.example) for the full list.

---

## Important Design Decisions

- **No OpenAI / paid APIs** — entirely open-source stack
- **Neon Postgres (Vercel Marketplace)** instead of deprecated Vercel Postgres
- **Modular parsing** — each parser (PDF, OCR, layout, form) is independent
- **LlamaIndex** orchestrates chunking, embedding, and retrieval
- **Citations** — every answer includes source chunks with page numbers
- **Separate ingestion service** — heavy OCR/parsing runs outside Vercel function limits

---

## License

MIT