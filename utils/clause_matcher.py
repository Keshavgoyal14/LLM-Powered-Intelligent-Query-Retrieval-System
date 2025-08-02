from langchain.text_splitter import RecursiveCharacterTextSplitter
from utils.embedding import get_vectorStore
from pymongo import MongoClient
from dotenv import load_dotenv
import asyncio
import hashlib
import os
import json

load_dotenv()

# MongoDB setup
mongo_uri = os.getenv("MONGO_URI")
mongo_client = MongoClient(mongo_uri)
mongo_db = mongo_client["vectorstore_cache"]
doc_cache_collection = mongo_db["doc_metadata"]
CURRENT_VERSION = "v2"

def get_doc_hash(doc_url: str) -> str:
    return hashlib.md5(doc_url.encode()).hexdigest()

def is_document_indexed(doc_hash: str) -> bool:
    return doc_cache_collection.find_one({
        "doc_hash": doc_hash,
        "version": CURRENT_VERSION
    }) is not None

def mark_document_indexed(doc_hash: str, chunk_count: int):
    doc_cache_collection.update_one(
        {"doc_hash": doc_hash},
        {"$set": {
            "doc_hash": doc_hash,
            "chunk_count": chunk_count,
            "version": CURRENT_VERSION
        }},
        upsert=True
    )

def index_documents(docs, doc_hash):
    # Check if already indexed
    if is_document_indexed(doc_hash):
        print(f"✅ Vectorstore already indexed for {doc_hash}")
        return get_vectorStore()

    print(f"⚙️ Indexing new document {doc_hash}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
        length_function=len,
        separators=["\n\n", "\n", ". ", ", ", " "]
    )
    splits = text_splitter.split_documents(docs)
    print(f"🔍 Number of chunks: {len(splits)}")

    vector_store = get_vectorStore()

    for i, split in enumerate(splits):
        if i > 0:
            split.metadata["prev_content"] = splits[i - 1].page_content
        if i < len(splits) - 1:
            split.metadata["next_content"] = splits[i + 1].page_content

    # Add to Pinecone (or other vector store)
    batch_size = 50
    for i in range(0, len(splits), batch_size):
        batch = splits[i:i + batch_size]
        vector_store.add_documents(batch, namespace=doc_hash)

    mark_document_indexed(doc_hash, len(splits))
    print(f"💾 Vectorstore persisted info in MongoDB: {doc_hash}")
    return vector_store


async def retrieve_relevant_clauses(vector_store, question, namespace, top_k=5):
    try:
        print(f"🔍 Retrieving for: {question}")
        primary_results = await asyncio.to_thread(
            vector_store.similarity_search_with_score,
            question,
            k=top_k * 2,
            namespace=namespace
        )

        clean_results = []
        seen_content = set()

        for doc, score in primary_results:
            content = doc.page_content.strip()
            if score < 0.8 and content and content not in seen_content:
                context_parts = []
                if hasattr(doc.metadata, "prev_content"):
                    context_parts.append(doc.metadata["prev_content"])
                context_parts.append(content)
                if hasattr(doc.metadata, "next_content"):
                    context_parts.append(doc.metadata["next_content"])
                full_context = "\n".join(context_parts)
                clean_results.append(full_context)
                seen_content.add(content)

        if not clean_results:
            fallback = await asyncio.to_thread(
                vector_store.similarity_search,
                question,
                k=top_k,
                namespace=namespace
            )
            clean_results = [doc.page_content.strip() for doc in fallback if doc.page_content.strip()]

        return clean_results[:top_k] if clean_results else ["No relevant information found."]
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"❌ Retrieval error: {str(e)}")
