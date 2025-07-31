from fastapi import FastAPI, Header, HTTPException
from fastapi.openapi.utils import get_openapi
from schemas import QueryResponse, QueryRequest
from utils.llm_gemini import gemini_answer
from utils.document_loader import load_documents
from utils.clause_matcher import index_documents, retrieve_relevant_clauses
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
app = FastAPI()

TEAM_TOKEN = "76383ca924349758781a28503e0628a023bfaff20608d8fbb2d03f17ae19ef0e"

# ✅ Add Bearer Token to Swagger UI
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

    # Apply BearerAuth to all routes
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"BearerAuth": []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ✅ Endpoint with Bearer token check
@app.post("/api/v1/hackrx/run", response_model=QueryResponse)
async def run_query(
    req: QueryRequest,
    authorization: str = Header(None)
):
    # 🔒 Authorization
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    token = parts[1]
    if token != TEAM_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid team token")

    # 🧠 Vector Indexing
    namespace = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    docs = load_documents(req.documents)
    vector_store = index_documents(docs, namespace)

    # ❓ Process each question sequentially
    answers = []
    for question in req.questions:
        relevant_clauses = retrieve_relevant_clauses(vector_store, question, namespace)
        context = "\n".join(relevant_clauses) if isinstance(relevant_clauses, list) else str(relevant_clauses)
        answer = await gemini_answer(context, question)
        answers.append(answer)

    return {"answers": answers}
