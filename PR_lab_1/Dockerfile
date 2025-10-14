# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy the server and client scripts
COPY http_server_basic.py .
COPY client.py .

# Copy the website content
COPY website/ ./website/

# Create downloads directory
RUN mkdir -p downloads

# Expose port 8080 for the HTTP server
EXPOSE 8080

# Set default command to run the server
CMD ["python", "http_server_basic.py", "./website"]