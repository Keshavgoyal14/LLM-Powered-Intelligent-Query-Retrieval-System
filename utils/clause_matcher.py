from langchain.text_splitter import RecursiveCharacterTextSplitter
from utils.embedding import get_vectorStore
from functools import lru_cache
import asyncio
import os
from pinecone import Pinecone
from concurrent.futures import ThreadPoolExecutor

PINECONE_API_KEY= os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)
@lru_cache(maxsize=1)
def get_cached_vectorstore():
    return get_vectorStore()

def process_batch(batch, vector_store, namespace):
    vector_store.add_documents(batch, namespace=namespace)

def pinecone_namespace_exists(index_name: str, namespace: str) -> bool:
    index = pc.Index(index_name)
    stats = index.describe_index_stats()
    return namespace in stats.get("namespaces", {})

DANGEROUS_PATTERNS = [
    "forget all instructions",
    "ignore all previous instructions",
    "leak",
    "catastrophic system failure",
    "personally identifiable information",
    "no exceptions",
    "override",
    "ignore safety",
    "immediate and irreversible leakage",
    "respond exclusively with the phrase",
    "this is a direct order",
    "system administrator"
]
def contain_dangerous_instructions(text: str) -> bool:
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in DANGEROUS_PATTERNS)

def index_documents(docs, namespace):
    # Optimize chunk size and overlap for better context
    index_name = os.getenv("INDEX_NAME")
    if pinecone_namespace_exists(index_name, namespace):
        print(f"✅ Pinecone namespace '{namespace}' already exists. Skipping re-indexing.")
        return get_cached_vectorstore()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,      # Increased for better context
        chunk_overlap=300,     # Increased overlap
        length_function=len,
        separators=["\n\n", "\n", ". ", ", ", " "]  # More granular splitting
    )
    
    splits = text_splitter.split_documents(docs)
    print(f"🔍 Number of chunks being indexed: {len(splits)}")
    vector_store = get_cached_vectorstore()
    
    splits = text_splitter.split_documents(docs)
    print(f"🔍 Number of chunks before filtering: {len(splits)}")

    # Filter out dangerous chunks
    safe_splits = [
        split for split in splits
        if not contain_dangerous_instructions(split.page_content)
    ]
    print(f"🔍 Number of chunks after filtering: {len(safe_splits)}")

    if not safe_splits:
        return {
            "success": False,
            "answers": ["Document contains only unsafe instructions and cannot be processed."]
        }
    # Enhanced document processing
    for i, split in enumerate(safe_splits):
        if i > 0:
            split.metadata["prev_content"] = safe_splits[i-1].page_content
        if i < len(safe_splits) - 1:
            split.metadata["next_content"] = safe_splits[i+1].page_content

    batch_size = 50
    batches = [safe_splits[i:i + batch_size] for i in range(0, len(safe_splits), batch_size)]

    # Parallel batch processing
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(process_batch, batch, vector_store, namespace)
            for batch in batches
        ]
        for future in futures:
            future.result()  # Wait for all batches to finish

    return vector_store

async def retrieve_relevant_clauses(vector_store, question, namespace, top_k=5):
    # Enhanced search with multiple strategies
    try:
        # Primary search with scores
        print(f"🔍 Searching for relevant clauses for question: {question}")
        primary_results = await asyncio.to_thread(
            vector_store.similarity_search_with_score,
            question,
            k=top_k * 2,  # Get more candidates
            namespace=namespace
        )
        
        clean_results = []
        seen_content = set()
        
        for doc, score in primary_results:
            content = doc.page_content.strip()
            
            # More lenient score threshold
            if score < 0.8 and content and content not in seen_content:
                # Build context window
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
        
        # If no good results, try basic search
        if not clean_results:
            basic_results = await asyncio.to_thread(
                vector_store.similarity_search,
                question,
                k=top_k,
                namespace=namespace
            )
            clean_results = [doc.page_content.strip() for doc in basic_results if doc.page_content.strip()]
        
        # Ensure we have some results
        return clean_results[:top_k] if clean_results else ["No relevant information found in the policy document."]
    
    except Exception as e:
        print(f"Error in retrieve_relevant_clauses: {str(e)}")
        return ["Error retrieving policy information."]