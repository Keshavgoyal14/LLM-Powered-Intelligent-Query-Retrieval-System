from langchain.text_splitter import RecursiveCharacterTextSplitter
from utils.embedding import get_vectorStore
import asyncio
from pymongo import MongoClient
import os

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "finbot_cache")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "vectorstores")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]

def index_documents(docs, doc_hash):
    # Check if already indexed in Pinecone (flag in MongoDB)
    if collection.find_one({"_id": doc_hash, "indexed": True}):
        print(f"✅ Pinecone index already exists for: {doc_hash}")
        # Just reconnect to Pinecone index/namespace
        return get_vectorStore()

    print(f"⚙️ Creating new Pinecone index for: {doc_hash}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
        length_function=len,
        separators=["\n\n", "\n", ". ", ", ", " "]
    )
    splits = text_splitter.split_documents(docs)
    print(f"🔍 Number of chunks being indexed: {len(splits)}")

    vector_store = get_vectorStore()

    for i, split in enumerate(splits):
        if i > 0:
            split.metadata["prev_content"] = splits[i-1].page_content
        if i < len(splits) - 1:
            split.metadata["next_content"] = splits[i+1].page_content

    batch_size = 50
    for i in range(0, len(splits), batch_size):
        batch = splits[i:i + batch_size]
        vector_store.add_documents(batch, namespace=doc_hash)

    # Mark as indexed in MongoDB
    collection.update_one(
        {"_id": doc_hash},
        {"$set": {"indexed": True}},
        upsert=True
    )
    print(f"💾 Marked Pinecone index as indexed in MongoDB for: {doc_hash}")

    return vector_store

async def retrieve_relevant_clauses(vector_store, question, namespace, top_k=5):
    # Enhanced search with multiple strategies
    try:
        print(f"🔍 Searching for relevant clauses for question: {question}")
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
                if len(full_context.strip()) > 0:
                    clean_results.append(full_context)
                    seen_content.add(content)

        if not clean_results:
            basic_results = await asyncio.to_thread(
                vector_store.similarity_search,
                question,
                k=top_k,
                namespace=namespace
            )
            clean_results = [doc.page_content.strip() for doc in basic_results if doc.page_content.strip()]

        return clean_results[:top_k] if clean_results else ["No relevant information found in the policy document."]

    except Exception as e:
        print(f"Error in retrieve_relevant_clauses: {str(e)}")
        return ["Error retrieving policy information."]