from urllib.parse import urlparse
import os
import tempfile
import requests
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.schema import Document
def load_documents(url: str):
    print(f"Loading document from URL: {url}")

    # Extract file extension
    parsed_url = urlparse(url)
    path = parsed_url.path
    extension = os.path.splitext(path)[1].lower()

    allowed_ext = [".pdf", ".docx", ".txt"]
    if extension not in allowed_ext:
        print(f"Unsupported file type: {extension}")
        return []
    # Set max size (500 MB)
    max_size = 500 * 1024 * 1024  # in bytes

    # HEAD request to check size before downloading
    try:
        head = requests.head(url, allow_redirects=True, timeout=10)
        content_length = head.headers.get("Content-Length")
        if content_length:
            size_bytes = int(content_length)
            if size_bytes > max_size:
                raise ValueError(f"File size exceeds the maximum limit of {max_size} bytes ({size_bytes} bytes).")
    except Exception as e:
        print(f"HEAD request failed or no size info: {e}")
        # Continue — we will still try to download, but could add streaming limit here

    # Now safe to download
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    # If no Content-Length header, double-check size after download
    if not content_length and len(response.content) > max_size:
        print(f"File size exceeds limit after download")
        return None
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
        temp.write(response.content)
        temp.flush()

        # Choose loader based on extension
        if extension == ".pdf":
            loader = PyPDFLoader(temp.name)
        elif extension == ".docx":
            loader = Docx2txtLoader(temp.name)
        elif extension == ".txt":
            loader = TextLoader(temp.name)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

        docs = loader.load()

    # Clean up temp file
    os.unlink(temp.name)
    return docs
