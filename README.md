# LLM-Powered Intelligent Query-Retrieval System

A FastAPI backend for intelligent document ingestion, search, Q&A, and content moderation using LangChain, Gemini, OCR, Hugging Face moderation, and vector search.  
Supports PDF, DOCX, TXT, PPTX (with OCR for embedded images), Excel, and image files.

---

## Tech Stack

- **FastAPI** – High-performance Python web framework for APIs
- **LangChain** – Document loaders, chunking, and vector search
- **Gemini (Google Generative AI)** – LLM-powered question answering
- **EasyOCR** – Optical Character Recognition for images and PPTX-embedded images
- **Hugging Face Moderation API** – Content moderation for questions and document chunks
- **Pinecone** – Vector database for semantic search (if enabled)
- **Tesseract-OCR** – Backend OCR engine for EasyOCR
- **Python** – Core programming language

---

## Features

- **Domain-Specific Q&A:** Optimized for the following domains:
  - **Insurance:** Policies, claims, coverage, regulatory compliance, etc.
  - **Legal:** Law, regulations, compliance, contracts, statutory requirements, etc.
  - **HR:** Human resources, employee policies, workplace regulations, etc.
  - **Contracts:** Contractual terms, obligations, agreement structures, etc.
- **Document Ingestion:** Upload and process PDF, DOCX, TXT, PPTX, XLSX, PNG, JPG, JPEG files.
- **Text Extraction:** Uses LangChain loaders for text-based files, EasyOCR for images, and custom OCR for images embedded in PPTX slides.
- **.aspx Link Resolution:** Automatically resolves Office Online `.aspx` links to the real file.
- **Vector Search:** Indexes documents for semantic and keyword-based retrieval.
- **Question Answering:** Answers user queries using Gemini and retrieved document context, with domain-aware prompts.
- **Content Moderation:** Uses Hugging Face moderation API to check for unsafe or inappropriate content in both user questions and document chunks before indexing or answering.
- **Security:** Blocks broad or privacy-violating queries with customizable forbidden patterns.
- **Production Ready:** Handles temp files safely and cleans up resources.

---

## Requirements

- Python 3.8+
- [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) (for EasyOCR)
- [Hugging Face account & API key](https://huggingface.co/docs/api-inference/index) (for content moderation)
- All Python dependencies in `requirements.txt`

---

## Setup

1. **Clone the repository**
2. **Install Python dependencies:**
    ```sh
    pip install -r requirements.txt
    ```
3. **Install Tesseract-OCR:**
    - Download and install from [here](https://github.com/tesseract-ocr/tesseract).
    - Add the install directory to your system PATH.
4. **Set up Hugging Face API key:**
    - Get your API key from [Hugging Face](https://huggingface.co/settings/tokens).
    - Add it to your environment variables or `.env` file as `HF_API_KEY`.

---

## Environment Variables

Create a `.env` file in your project root with the following variables:

```env
# Hugging Face API key for content moderation
HF_API_KEY=your_huggingface_api_key_here

# (Optional) Other environment variables as needed for your project
# Example: MongoDB connection string, Pinecone API key, Google API key, Gemini API key, etc.
MONGODB_URI=your_mongodb_uri_here
PINECONE_API_KEY=your_pinecone_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

- Replace the values with your actual keys and connection strings.
- The `HF_API_KEY` is required for Hugging Face moderation to work.

---

## Usage

- **Start the API:**
    ```sh
    uvicorn main:app --reload
    ```
- **POST documents and questions to `/api/v1/hackrx/run`**  
  (see your FastAPI docs for schema)

---

## API Usage

### Request Format

```json
{
  "documents": "https://example.com/document.pdf",
  "questions": [
    "Who is eligible for this policy?",
    "How can a claim be filed?",
    "What documents are required for reimbursement?"
  ]
}
```

### Response Format

```json
{
  "answers": [
    "Eligibility includes individuals aged 18-65 with no pre-existing critical illnesses.",
    "A claim can be filed online through the portal or by contacting customer support.",
    "Required documents for reimbursement include the claim form, hospital bills, and identity proof."
  ]
}
```

### Example with curl

```sh
curl -X POST "https://your-api-url.com/api/v1/hackrx/run" \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/document.pdf",
    "questions": ["Who is eligible for this policy?"]
  }'
```

---

## API Documentation

You can explore and test the API using the interactive Swagger UI:

👉 **[https://hackerx-finbotapi.onrender.com/docs](https://hackerx-finbotapi.onrender.com/docs)**

---

## File Support

| File Type | Loader/Method                | Notes                                 |
|-----------|-----------------------------|---------------------------------------|
| PDF       | PyPDFLoader                 | Text extraction                       |
| DOCX      | Docx2txtLoader              | Text extraction                       |
| TXT       | TextLoader                  | Plain text                            |
| PPTX      | Custom + EasyOCR            | OCR on embedded images in slides      |
| XLSX/XLS  | UnstructuredExcelLoader     | Text extraction                       |
| PNG/JPG   | EasyOCR                     | OCR                                   |

---

## Content Moderation

- **Hugging Face moderation** is used to check for unsafe, toxic, or inappropriate content:
    - **During indexing:** Each document chunk is checked before being indexed. Unsafe chunks are skipped.
    - **During Q&A:** Each user question is checked before answering. Unsafe questions are blocked with a safe response.
- Moderation is enforced using the Hugging Face API and can be customized for your use case.

---

## Security

- Forbidden queries (e.g., "all customer database", "export database") are blocked.
- Only specific, legitimate queries about customer details are answered.
- Moderation ensures no unsafe content is indexed or answered.

---

## Notes

- For best OCR results, ensure Tesseract is installed and working.
- All temp files are cleaned up after processing.
- PPTX text extraction is limited to images embedded in slides (not text boxes or tables).
- Hugging Face moderation requires a valid API key and internet access.
- **This system is optimized for insurance, legal, HR, and contracts domains.**

---

## License

MIT License

---

## Authors

- Keshav Goyal