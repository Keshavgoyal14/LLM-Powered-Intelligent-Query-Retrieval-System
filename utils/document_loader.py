from urllib.parse import urlparse
import os
import tempfile
import requests
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

def load_documents(url: str):
    print(f"Loading document from URL: {url}")
    response = requests.get(url)
    parsed_url = urlparse(url)
    path = parsed_url.path  # Only the path, no query string
    extension = os.path.splitext(path)[1].lower()  # Get the actual file extension

    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
        temp.write(response.content)
        temp.flush()

        if extension == ".pdf":
            loader = PyPDFLoader(temp.name)
        elif extension == ".docx":
            loader = Docx2txtLoader(temp.name)
        elif extension == ".txt":
            loader = TextLoader(temp.name)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

        docs = loader.load()

    os.unlink(temp.name)
    return docs