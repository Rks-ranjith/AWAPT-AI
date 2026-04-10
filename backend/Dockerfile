FROM python:3.10-slim

# Install system dependencies needed for lxml, networkx, async networking, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Let uvicorn map ports
EXPOSE 8000

ENV PYTHONPATH=/app
CMD ["uvicorn", "awap.main:app", "--host", "0.0.0.0", "--port", "8000"]
