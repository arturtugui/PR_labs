from socket import *
import sys
import os

def parse_http_response(response_data):
    """Parse HTTP response into headers and body"""
    # Split response into headers and body
    response_str = response_data.decode('utf-8', errors='ignore')
    
    try:
        # Find the end of headers (double CRLF)
        header_end = response_str.find('\r\n\r\n')
        if header_end == -1:
            return None, None, None
        
        headers_part = response_str[:header_end]
        body_start = header_end + 4
        
        # Parse status line
        lines = headers_part.split('\r\n')
        status_line = lines[0]
        status_code = int(status_line.split()[1])
        
        # Parse headers
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Get content length
        content_length = int(headers.get('content-length', 0))
        
        return status_code, headers, body_start
        
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None, None, None

def main():
    # Check command line arguments
    if len(sys.argv) != 5:
        print("Usage: python client.py server_host server_port url_path directory")
        print("Example: python client.py localhost 8080 /index.html ./downloads")
        print("Example: python client.py localhost 8080 /sample.pdf ./downloads")
        sys.exit(1)
    
    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    url_path = sys.argv[3]
    save_directory = sys.argv[4]
    
    # Create save directory if it doesn't exist
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
        print(f"Created directory: {save_directory}")
    
    print(f"Connecting to {server_host}:{server_port}")
    print(f"Requesting: {url_path}")
    print(f"Save directory: {save_directory}")
    print("-" * 50)
    
    try:
        # Create TCP socket
        client_socket = socket(AF_INET, SOCK_STREAM)
        
        # Connect to server
        client_socket.connect((server_host, server_port))
        
        # Create HTTP GET request
        http_request = f"GET {url_path} HTTP/1.1\r\nHost: {server_host}:{server_port}\r\nConnection: close\r\n\r\n"
        
        # Send request
        client_socket.send(http_request.encode())
        print(f"Sent request:\n{http_request}")
        
        # Receive response
        response_data = b""
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            response_data += data
        
        client_socket.close()
        
        # Parse response
        status_code, headers, body_start = parse_http_response(response_data)
        
        if status_code is None:
            print("Failed to parse HTTP response")
            return
        
        print(f"Status Code: {status_code}")
        print(f"Headers: {headers}")
        print("-" * 50)
        
        # Handle response based on status code
        if status_code != 200:
            print(f"Error: Server returned status {status_code}")
            # Print the error page content
            body = response_data[body_start:].decode('utf-8', errors='ignore')
            print("Response body:")
            print(body)
            return
        
        # Get content type
        content_type = headers.get('content-type', 'unknown')
        print(f"Content-Type: {content_type}")
        
        # Handle based on content type
        if content_type.startswith('text/html'):
            # HTML - print body as-is
            body = response_data[body_start:].decode('utf-8', errors='ignore')
            print("\\nHTML Content:")
            print("=" * 50)
            print(body)
            
        elif content_type.startswith('image/png') or content_type.startswith('application/pdf'):
            # Binary files - save to directory
            body = response_data[body_start:]
            
            # Extract filename from URL path
            filename = os.path.basename(url_path)
            if not filename:
                # If no filename in path, create one based on content type
                if content_type.startswith('image/png'):
                    filename = 'downloaded_image.png'
                elif content_type.startswith('application/pdf'):
                    filename = 'downloaded_document.pdf'
            
            # Full path for saving
            save_path = os.path.join(save_directory, filename)
            
            # Save file
            with open(save_path, 'wb') as f:
                f.write(body)
            
            print(f"\\nFile saved successfully!")
            print(f"Saved to: {save_path}")
            print(f"File size: {len(body)} bytes")
            
        else:
            print(f"\\nUnsupported content type: {content_type}")
            print("Raw response body:")
            try:
                body = response_data[body_start:].decode('utf-8', errors='ignore')
                print(body)
            except:
                print("Binary data - cannot display as text")
    
    except Exception as e:
        print(f"Error: {e}")
        
if __name__ == "__main__":
    main()