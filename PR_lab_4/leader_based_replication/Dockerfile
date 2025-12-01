FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY kv_store.py .
COPY replication_manager.py .

# Expose default port (will be overridden by docker-compose)
EXPOSE 8000

# Run the Flask server
CMD ["python", "server.py"]
