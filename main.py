from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from schemas import QueryResponse, QueryRequest
from utils.llm_gemini import gemini_answer
from utils.document_loader import load_documents
from utils.clause_matcher import index_documents, retrieve_relevant_clauses
from dotenv import load_dotenv
from datetime import datetime
import asyncio
from functools import lru_cache
import hashlib

load_dotenv()

# Initialize FastAPI with metadata
app = FastAPI(
    title="Insurance Policy Q&A API",
    description="API for retrieving answers from insurance policy documents",
    version="1.0.0"
)

# Add middlewares
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
TEAM_TOKEN = "76383ca924349758781a28503e0628a023bfaff20608d8fbb2d03f17ae19ef0e"

# Document cache
document_cache = {}

def get_document_hash(document_url: str) -> str:
    return hashlib.md5(document_url.encode()).hexdigest()

def get_cached_vector_store(doc_hash: str):
    return document_cache.get(doc_hash)

# Swagger UI configuration
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Retrieval System API",
        version="1.0.0",
        description="Run insurance document queries",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"BearerAuth": []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Health check endpoint
@app.api_route("/", methods=["GET", "HEAD"])
async def health_check(request: Request):
    if request.method == "HEAD":
        return
    return {"message": "Server is alive!"}

# Main API endpoint
@app.post("/api/v1/hackrx/run", response_model=QueryResponse)
async def run_query(
    req: QueryRequest,
    authorization: str = Header(None)
):
    # Authorization check
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    token = parts[1]
    if token != TEAM_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid team token")

    try:
        # Generate document hash and check cache
        doc_hash = get_document_hash(req.documents)
        vector_store = get_cached_vector_store(doc_hash)
        
        if not vector_store:
            # Process document if not in cache
            docs = load_documents(req.documents)
            vector_store = index_documents(docs, doc_hash)
            document_cache[doc_hash] = vector_store

        # Process questions in batches
        batch_size = 3
        answers = []
        
        async def process_question(question):
            try:
                relevant_clauses = await retrieve_relevant_clauses(
                    vector_store, 
                    question, 
                    doc_hash, 
                    top_k=8
                )
                context = "\n".join(relevant_clauses) if isinstance(relevant_clauses, list) else str(relevant_clauses)
                return await gemini_answer(context, question)
            except Exception as e:
                return f"Error processing question: {str(e)}"

        # Process questions in parallel with batching
        for i in range(0, len(req.questions), batch_size):
            batch = req.questions[i:i + batch_size]
            batch_answers = await asyncio.gather(
                *(process_question(q) for q in batch)
            )
            answers.extend(batch_answers)

        return {"answers": answers}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=4
    )