# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy the server script and test files
COPY http_server_basic.py .
COPY test_performance.py .
COPY test_race_condition.py .
COPY test_rate_limiting.py .

# Copy the website content and templates
COPY website/ ./website/
COPY templates/ ./templates/

# Create downloads directory
RUN mkdir -p downloads

# Expose port 8080 for the HTTP server
EXPOSE 8080

# Set default command to run the server
CMD ["python", "http_server_basic.py", "./website"]