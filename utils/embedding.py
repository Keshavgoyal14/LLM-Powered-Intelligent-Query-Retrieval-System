from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME")
PINECONE_DIM = 768  # Gemini embeddings output dimension
PINECONE_REGION = "us-east-1"
PINECONE_CLOUD = "aws"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

pc = Pinecone(api_key=PINECONE_API_KEY)

if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=PINECONE_DIM,
        metric='euclidean',
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION
        )
    )

def get_vectorStore():
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",  # Gemini embedding model
        google_api_key=GEMINI_API_KEY
    )
    vector_store = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embeddings,
        pinecone_api_key=PINECONE_API_KEY
    )
    return vector_store