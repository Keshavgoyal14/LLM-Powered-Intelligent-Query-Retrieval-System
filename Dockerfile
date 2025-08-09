# Use PyTorch base image with Python 3.10 to avoid rebuilding heavy ML libs
FROM pytorch/pytorch:2.2.0-cuda11.8-cudnn8-runtime

WORKDIR /app

# Install system dependencies for OCR, PDF, and image processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        poppler-utils \
        gcc \
        ffmpeg \
        && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project files
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Use Gunicorn with Uvicorn workers for production
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]
