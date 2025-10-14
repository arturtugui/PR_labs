from socket import *
import os
import sys

# Check command line arguments
if len(sys.argv) != 2:
    print("Usage: python http_server_basic.py <directory>")
    print("Example: python http_server_basic.py ./website")
    sys.exit(1)

# Get the directory to serve from command line
serve_directory = sys.argv[1]

# Check if the directory exists
if not os.path.isdir(serve_directory):
    print(f"Error: Directory '{serve_directory}' does not exist!")
    sys.exit(1)

print(f"Serving files from directory: {serve_directory}")

serverPort = 8080  # Changed to 8080 (common HTTP port)

# Create a TCP welcoming socket
serverSocket = socket(AF_INET, SOCK_STREAM)

# Allow reusing the address (helpful during development)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

# Bind the socket to the port
serverSocket.bind(('', serverPort))

# Listen for incoming connections
serverSocket.listen(1)
print(f'HTTP Server is ready at http://localhost:{serverPort}')

while True:
    # Accept a new connection
    connectionSocket, addr = serverSocket.accept()
    print(f"Connection from {addr}")

    try:
        # Receive the HTTP request
        request = connectionSocket.recv(1024).decode()
        print("Received request:")
        #print(request)
        #print("-" * 40)

        # Parse the first line of the request
        if request:
            first_line = request.split('\n')[0]
            method, path, version = first_line.split()
            print(f"Method: {method}, Path: {path}, Version: {version}")

            # Create a simple HTTP response
            # Build the file path from the requested path
            if path == '/':
                # Default to index.html for root path
                file_path = os.path.join(serve_directory, 'index.html')
            else:
                # Remove leading slash and join with serve directory
                file_path = os.path.join(serve_directory, path.lstrip('/'))
            
            print(f"Looking for file: {file_path}")
            
            # Check if the file exists
            if os.path.isfile(file_path):
                # Get file extension to determine content type
                _, ext = os.path.splitext(file_path.lower())
                
                # Determine content type based on extension
                if ext == '.html' or ext == '.htm':
                    content_type = 'text/html'
                    # Read text files in text mode
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    response_body = file_content
                elif ext == '.png':
                    content_type = 'image/png'
                    # Read binary files in binary mode
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    response_body = file_content
                elif ext == '.pdf':
                    content_type = 'application/pdf'
                    # Read binary files in binary mode
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    response_body = file_content
                else:
                    # Unknown file type - return 404
                    response_body = """<html>
<head><title>404 Not Found</title></head>
<body>
<h1>404 - Unsupported File Type</h1>
<p>The server doesn't support this file type.</p>
</body>
</html>"""
                    response = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
                    connectionSocket.send(response.encode())
                    continue
                
                # Create HTTP response for supported files
                if isinstance(response_body, str):
                    # Text files (HTML)
                    response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(response_body.encode('utf-8'))}\r\n\r\n{response_body}"
                    connectionSocket.send(response.encode('utf-8'))
                else:
                    # Binary files (PNG, PDF)
                    response_headers = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(response_body)}\r\n\r\n"
                    connectionSocket.send(response_headers.encode('utf-8'))
                    connectionSocket.send(response_body)
                
            else:
                # File not found - return 404
                response_body = """<html>
<head><title>404 Not Found</title></head>
<body>
<h1>404 - File Not Found</h1>
<p>The requested file was not found on this server.</p>
</body>
</html>"""
                response = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
                connectionSocket.send(response.encode())

    except Exception as e:
        print(f"Error: {e}")
        # Send a simple error response
        error_response = "HTTP/1.1 500 Internal Server Error\r\n\r\nServer Error"
        connectionSocket.send(error_response.encode())

    finally:
        # Close the connection
        print("Closing connection")
        connectionSocket.close()