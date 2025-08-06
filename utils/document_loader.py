from urllib.parse import urlparse, parse_qs, unquote
import os
import tempfile
import requests
import zipfile
import easyocr
from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader, Docx2txtLoader, TextLoader, UnstructuredExcelLoader
)

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)

def resolve_aspx(url: str) -> str:
    parsed = urlparse(url)
    if parsed.path.lower().endswith(".aspx"):
        qs = parse_qs(parsed.query)
        if "src" in qs:
            real_url = unquote(qs["src"][0])
            print(f"Resolved .aspx to: {real_url}")
            return real_url
    return url

def extract_images_from_pptx(pptx_path):
    """Extracts embedded images from PPTX file."""
    images = []
    with zipfile.ZipFile(pptx_path, 'r') as z:
        for file in z.namelist():
            if file.startswith("ppt/media/") and file.lower().endswith((".png", ".jpg", ".jpeg")):
                img_data = z.read(file)
                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file)[1])
                temp_img.write(img_data)
                temp_img.close()
                images.append(temp_img.name)
    return images

def pptx_images_with_ocr(pptx_path, url):
    """Extract images from PPTX and run OCR on each."""
    docs = []
    for img_path in extract_images_from_pptx(pptx_path):
        try:
            text_results = reader.readtext(img_path, detail=0)
            extracted_text = "\n".join(text_results).strip() or "[No readable text found]"
            docs.append(Document(page_content=extracted_text, metadata={"source": url, "image_file": os.path.basename(img_path)}))
        finally:
            os.unlink(img_path)  # Remove temp image after processing
    return docs

def load_documents(url: str):
    print(f"Loading document from URL: {url}")
    url = resolve_aspx(url)

    parsed_url = urlparse(url)
    extension = os.path.splitext(parsed_url.path)[1].lower()

    allowed_ext = [
        ".pdf", ".docx", ".txt", ".pptx", ".xlsx", ".xls", ".png", ".jpg", ".jpeg"
    ]
    if extension not in allowed_ext:
        print(f"Unsupported file type: {extension}")
        return []

    max_size = 500 * 1024 * 1024

    try:
        head = requests.head(url, allow_redirects=True, timeout=10)
        content_length = head.headers.get("Content-Length")
        if content_length and int(content_length) > max_size:
            print(f"File too large: {content_length} bytes.")
            return []
    except Exception as e:
        print(f"HEAD request failed: {e}")
        content_length = None

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    if not content_length and len(response.content) > max_size:
        print("File size exceeds limit after download")
        return []

    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
        temp.write(response.content)
        temp.flush()
        temp_path = temp.name

    try:
        if extension == ".pdf":
            docs = PyPDFLoader(temp_path).load()
        elif extension == ".docx":
            docs = Docx2txtLoader(temp_path).load()
        elif extension == ".txt":
            docs = TextLoader(temp_path).load()
        elif extension == ".pptx":
            docs = pptx_images_with_ocr(temp_path, url)
        elif extension in [".xlsx", ".xls"]:
            docs = UnstructuredExcelLoader(temp_path).load()
        elif extension in [".png", ".jpg", ".jpeg"]:
            text_results = reader.readtext(temp_path, detail=0)
            extracted_text = "\n".join(text_results).strip() or "[No readable text found in image]"
            docs = [Document(page_content=extracted_text, metadata={"source": url})]
        else:
            docs = []
    finally:
        os.unlink(temp_path)

    return docs
