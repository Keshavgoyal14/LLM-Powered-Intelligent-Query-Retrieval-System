from langchain.text_splitter import RecursiveCharacterTextSplitter
from utils.embedding import get_vectorStore

def index_documents(docs, namespace):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    splits = text_splitter.split_documents(docs)
    
    vector_store = get_vectorStore()
    vector_store.add_documents(splits, namespace=namespace)
    return vector_store

def retrieve_relevant_clauses(vector_store, question, namespace, top_k=8):
    results = vector_store.similarity_search(question, k=top_k, namespace=namespace)
    return "\n\n".join([doc.page_content for doc in results])