import socket
import os
import sys
from pathlib import Path
from urllib.parse import unquote

def get_content_type(file_path):
    """Determine Content-Type based on file extension"""
    ext = Path(file_path).suffix.lower()
    content_types = {
        '.html': 'text/html',
        '.htm': 'text/html',
        '.pdf': 'application/pdf',
        '.png': 'image/png',
    }
    return content_types.get(ext, None)

def generate_directory_listing(directory_path, url_path):
    """Generate HTML page with directory contents"""
    try:
        entries = os.listdir(directory_path)
        entries.sort()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Directory listing for {url_path}</title>
</head>
<body>
    <h1>Directory listing for {url_path}</h1>
    <hr>
    <ul>
"""
        
        # Add parent directory link if not root
        if url_path != '/':
            parent = str(Path(url_path).parent).replace('\\', '/')
            if parent == '.':
                parent = '/'
            html += f'        <li><a href="{parent}">../</a></li>\n'
        
        # List directories first, then files
        dirs = []
        files = []
        
        for entry in entries:
            full_path = os.path.join(directory_path, entry)
            if os.path.isdir(full_path):
                dirs.append(entry)
            else:
                files.append(entry)
        
        for dir_name in dirs:
            link_path = f"{url_path.rstrip('/')}/{dir_name}/"
            html += f'        <li><a href="{link_path}">{dir_name}/</a></li>\n'
        
        for file_name in files:
            link_path = f"{url_path.rstrip('/')}/{file_name}"
            html += f'        <li><a href="{link_path}">{file_name}</a></li>\n'
        
        html += """    </ul>
    <hr>
</body>
</html>"""
        
        return html.encode('utf-8')
    except Exception as e:
        print(f"Error generating directory listing: {e}")
        return None

def handle_request(connection_socket, base_directory):
    """Handle a single HTTP request"""
    try:
        # Receive the request
        request = connection_socket.recv(4096).decode('utf-8')
        
        if not request:
            return
        
        # Parse the request line
        lines = request.split('\r\n')
        request_line = lines[0]
        print(f"Request: {request_line}")
        
        # Parse method and path
        parts = request_line.split()
        if len(parts) < 2:
            send_error(connection_socket, 400, "Bad Request")
            return
        
        method = parts[0]
        url_path = unquote(parts[1])  # Decode URL encoding
        
        # Only support GET
        if method != 'GET':
            send_error(connection_socket, 405, "Method Not Allowed")
            return
        
        # Construct file path
        # Remove leading slash and normalize path
        relative_path = url_path.lstrip('/')
        if not relative_path:
            relative_path = '.'
        
        file_path = os.path.normpath(os.path.join(base_directory, relative_path))
        
        # Security check: ensure the path is within base_directory
        base_abs = os.path.abspath(base_directory)
        file_abs = os.path.abspath(file_path)
        
        if not file_abs.startswith(base_abs):
            send_error(connection_socket, 403, "Forbidden")
            return
        
        # Check if path exists
        if not os.path.exists(file_path):
            send_error(connection_socket, 404, "Not Found")
            return
        
        # If it's a directory, generate listing
        if os.path.isdir(file_path):
            directory_html = generate_directory_listing(file_path, url_path)
            if directory_html:
                response = b"HTTP/1.1 200 OK\r\n"
                response += b"Content-Type: text/html; charset=utf-8\r\n"
                response += f"Content-Length: {len(directory_html)}\r\n".encode()
                response += b"\r\n"
                response += directory_html
                connection_socket.sendall(response)
            else:
                send_error(connection_socket, 500, "Internal Server Error")
            return
        
        # It's a file - check if we support this type
        content_type = get_content_type(file_path)
        if content_type is None:
            send_error(connection_socket, 415, "Unsupported Media Type")
            return
        
        # Read and send the file
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            response = b"HTTP/1.1 200 OK\r\n"
            response += f"Content-Type: {content_type}\r\n".encode()
            response += f"Content-Length: {len(file_content)}\r\n".encode()
            response += b"\r\n"
            response += file_content
            
            connection_socket.sendall(response)
            print(f"Sent {file_path} ({content_type})")
            
        except Exception as e:
            print(f"Error reading file: {e}")
            send_error(connection_socket, 500, "Internal Server Error")
            
    except Exception as e:
        print(f"Error handling request: {e}")
        send_error(connection_socket, 500, "Internal Server Error")

def send_error(connection_socket, status_code, status_message):
    """Send an HTTP error response"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{status_code} {status_message}</title>
</head>
<body>
    <h1>{status_code} {status_message}</h1>
</body>
</html>"""
    
    response = f"HTTP/1.1 {status_code} {status_message}\r\n".encode()
    response += b"Content-Type: text/html; charset=utf-8\r\n"
    response += f"Content-Length: {len(html)}\r\n".encode()
    response += b"\r\n"
    response += html.encode('utf-8')
    
    try:
        connection_socket.sendall(response)
    except:
        pass

def main():
    if len(sys.argv) != 2:
        print("Usage: python server.py <directory>")
        sys.exit(1)
    
    base_directory = sys.argv[1]
    
    if not os.path.isdir(base_directory):
        print(f"Error: {base_directory} is not a valid directory")
        sys.exit(1)
    
    server_port = 8080
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", server_port))
    server_socket.listen(5)
    
    print(f"HTTP Server started on port {server_port}")
    print(f"Serving directory: {os.path.abspath(base_directory)}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            connection_socket, addr = server_socket.accept()
            print(f"\nConnection from {addr}")
            handle_request(connection_socket, base_directory)
            connection_socket.close()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
