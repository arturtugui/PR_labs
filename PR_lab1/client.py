import socket
import sys
import os

def parse_response(response_data):
    """Parse HTTP response into headers and body"""
    try:
        # Find the end of headers (empty line)
        header_end = response_data.find(b'\r\n\r\n')
        if header_end == -1:
            return None, None, response_data
        
        headers_raw = response_data[:header_end].decode('utf-8', errors='ignore')
        body = response_data[header_end + 4:]
        
        # Parse status line
        lines = headers_raw.split('\r\n')
        status_line = lines[0]
        status_parts = status_line.split(' ', 2)
        status_code = int(status_parts[1]) if len(status_parts) > 1 else 0
        
        # Parse headers
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        return status_code, headers, body
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None, None, response_data

def get_content_type(headers):
    """Extract content type from headers"""
    content_type = headers.get('content-type', '')
    # Remove charset and other parameters
    return content_type.split(';')[0].strip()

def main():
    if len(sys.argv) != 5:
        print("Usage: python client.py <server_host> <server_port> <url_path> <save_directory>")
        print("Example: python client.py localhost 8080 /index.html ./downloads")
        sys.exit(1)
    
    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    url_path = sys.argv[3]
    save_directory = sys.argv[4]
    
    # Ensure url_path starts with /
    if not url_path.startswith('/'):
        url_path = '/' + url_path
    
    # Create save directory if it doesn't exist
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    
    # Create socket and connect
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_host, server_port))
        
        # Send HTTP GET request
        request = f"GET {url_path} HTTP/1.1\r\n"
        request += f"Host: {server_host}\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"
        
        client_socket.sendall(request.encode())
        
        # Receive response
        response_data = b''
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response_data += chunk
        
        client_socket.close()
        
        # Parse response
        status_code, headers, body = parse_response(response_data)
        
        if status_code is None:
            print("Error: Could not parse response")
            return
        
        print(f"Status: {status_code}")
        print(f"Content-Type: {headers.get('content-type', 'unknown')}")
        print(f"Content-Length: {len(body)} bytes\n")
        
        if status_code != 200:
            print(f"Error: Server returned status {status_code}")
            print(body.decode('utf-8', errors='ignore'))
            return
        
        content_type = get_content_type(headers)
        
        # Handle based on content type
        if content_type == 'text/html':
            # Print HTML to console
            print("=" * 60)
            print("HTML Content:")
            print("=" * 60)
            print(body.decode('utf-8', errors='ignore'))
            print("=" * 60)
            
        elif content_type in ['application/pdf', 'image/png']:
            # Save binary files
            filename = os.path.basename(url_path.rstrip('/'))
            if not filename:
                # If no filename, use a default based on type
                ext = '.pdf' if content_type == 'application/pdf' else '.png'
                filename = 'download' + ext
            
            save_path = os.path.join(save_directory, filename)
            
            with open(save_path, 'wb') as f:
                f.write(body)
            
            print(f"File saved to: {save_path}")
            print(f"Size: {len(body)} bytes")
        else:
            print(f"Unsupported content type: {content_type}")
            print("Body preview:")
            print(body[:200])
    
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {server_host}:{server_port}")
        print("Make sure the server is running.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()