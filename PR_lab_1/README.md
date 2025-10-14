# PR Lab 1: HTTP File Server

A simple HTTP file server implemented with Python sockets, containerized with Docker.

## Features

- HTTP file server with TCP sockets
- Serves HTML, PNG, and PDF files
- Directory listing for nested directories
- HTTP client for downloading files
- Command-line directory argument
- 404 error handling
- Docker containerization

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed

### Running the Server

1. **Start the HTTP server:**

   ```bash
   docker-compose up -d
   ```

2. **Access the server:**

   - Open browser: http://localhost:8080
   - Server serves files from `website/` directory

3. **View logs:**

   ```bash
   docker-compose logs -f http-server
   ```

4. **Stop the server:**
   ```bash
   docker-compose down
   ```

### Testing with HTTP Client

1. **Start client container:**

   ```bash
   docker-compose --profile client up -d
   ```

2. **Run client commands:**

   ```bash
   # Download HTML file (prints content)
   docker-compose exec http-client python client.py http-server 8080 /index.html ./downloads

   # Download PDF file (saves to downloads)
   docker-compose exec http-client python client.py http-server 8080 /CS_lab_1.pdf ./downloads

   # Download PNG image (saves to downloads)
   docker-compose exec http-client python client.py http-server 8080 /tumblr.png ./downloads

   # Test directory listing
   docker-compose exec http-client python client.py http-server 8080 /documents/ ./downloads
   ```

3. **View downloaded files:**
   ```bash
   ls downloads/
   ```

## Development

### Local Development (without Docker)

1. **Start server:**

   ```bash
   python http_server_basic.py ./website
   ```

2. **Test client:**
   ```bash
   python client.py localhost 8080 /index.html ./downloads
   ```

### Building Docker Image

```bash
# Build image
docker-compose build

# Rebuild after changes
docker-compose build --no-cache
```

## Project Structure

```
.
├── Dockerfile                 # Docker container definition
├── docker-compose.yml        # Docker Compose configuration
├── http_server_basic.py       # HTTP server implementation
├── client.py                  # HTTP client implementation
├── website/                   # Website content directory
│   ├── index.html            # Main page
│   ├── about.html            # About page
│   ├── documents/            # PDF documents subdirectory
│   ├── images/               # Images subdirectory
│   ├── *.pdf                 # PDF files
│   └── *.png, *.jpg          # Image files
└── downloads/                 # Client download directory
```

## Lab Requirements Completed

### Base Requirements ✅

- [x] HTTP file server with TCP sockets
- [x] One HTTP request at a time
- [x] Command-line directory argument
- [x] HTTP request parsing
- [x] File reading from directory
- [x] HTTP response with headers
- [x] 404 for missing/unknown files
- [x] HTML, PNG, PDF support
- [x] Content directory with files
- [x] HTML with embedded image
- [x] **Docker Compose setup**

### Bonus Requirements ✅

- [x] **HTTP Client (2 points)** - Download files, print HTML
- [x] **Directory Listing (2 points)** - Browse nested directories
- [x] **Docker containerization** - Full Docker Compose setup

Total: **10/10 points** + all bonuses completed!
