from socket import *
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, 'templates')

# ===================================================================
# COUNTER LOCK CONFIGURATION
# ===================================================================
# Set to False to show race condition (naive implementation)
# Set to True to use locks (thread-safe implementation)
ENABLE_COUNTER_LOCKS = True  # Change to False to demonstrate race condition
# ===================================================================

# ===================================================================
# RATE LIMITING CONFIGURATION
# ===================================================================
# Set to False to disable rate limiting (for testing other features)
# Set to True to enable rate limiting functionality
ENABLE_RATE_LIMITING = True  # Change to True when testing rate limits
MAX_REQUESTS_PER_SECOND = 5
RATE_LIMIT_WINDOW = 1.0  # seconds

# Set to False to disable 1-second delay (needed for rate limiting tests)
# Set to True to enable 1-second delay (needed for threading/performance tests)
ENABLE_PROCESSING_DELAY = True  # Change to False when testing rate limits
# ===================================================================

# Global counter to track file hits
file_hits = {}

# Lock for thread-safe counter access
hits_lock = threading.Lock()

# Rate limiting: Track request timestamps per IP address
# Dictionary structure: {IP_address: [timestamp1, timestamp2, ...]}
request_history = {}
rate_limit_lock = threading.Lock()


def check_rate_limit(client_ip):
    """
    Check if client IP is within rate limit using sliding window algorithm.
    Returns True if request should be allowed, False if rate limit exceeded.
    """
    if not ENABLE_RATE_LIMITING:
        return True  # Rate limiting disabled
    
    current_time = time.time()
    
    with rate_limit_lock:
        # Initialize history for new IP
        if client_ip not in request_history:
            request_history[client_ip] = []
        
        # Remove timestamps older than the rate limit window (sliding window)
        cutoff_time = current_time - RATE_LIMIT_WINDOW
        request_history[client_ip] = [
            timestamp for timestamp in request_history[client_ip]
            if timestamp > cutoff_time
        ]
        
        # Check if rate limit exceeded (check BEFORE adding current request)
        recent_request_count = len(request_history[client_ip])
        
        if recent_request_count >= MAX_REQUESTS_PER_SECOND:
            # Rate limit exceeded - don't add timestamp
            print(f" Rate limit exceeded for {client_ip}: {recent_request_count} requests in last {RATE_LIMIT_WINDOW}s")
            return False
        
        # Within limit - add current request timestamp
        request_history[client_ip].append(current_time)
        print(f" Request allowed for {client_ip}: {recent_request_count + 1}/{MAX_REQUESTS_PER_SECOND} requests")
        return True


def send_rate_limit_response(connectionSocket):
    """Send 429 Too Many Requests response"""
    response_body = """<!DOCTYPE html>
<html>
<head>
    <title>429 Too Many Requests</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; }
        h1 { color: #d9534f; }
    </style>
</head>
<body>
    <h1>429 Too Many Requests</h1>
    <p>You have exceeded the rate limit.</p>
    <p>Maximum allowed: <strong>5 requests per second</strong></p>
    <p>Please wait a moment before trying again.</p>
</body>
</html>"""
    
    response = f"HTTP/1.1 429 Too Many Requests\r\n"
    response += f"Content-Type: text/html\r\n"
    response += f"Retry-After: 1\r\n"
    response += f"Content-Length: {len(response_body)}\r\n"
    response += f"\r\n{response_body}"
    
    connectionSocket.send(response.encode())


def load_template(template_name):
    """Load an HTML template file"""
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"<html><body><h1>Error</h1><p>Template {template_name} not found</p></body></html>"

def generate_directory_listing(directory_path, url_path):
    """Generate HTML directory listing with hit counts"""
    try:
        # Debug: show all tracked files
        print(f"\n=== Generating directory listing for: {directory_path} ===")
        print(f"Current file_hits dictionary: {file_hits}")
        print(f"===\n")
        
        # Get list of files and directories
        items = os.listdir(directory_path)
        items.sort()
        
        # Create HTML content with table for better formatting
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Directory listing for {url_path}</title>
    <style>
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Directory listing for {url_path}</h1>
    <hr>
    <table>
        <tr>
            <th>File / Directory</th>
            <th>Hits</th>
        </tr>"""
        
        # Add parent directory link if not root
        if url_path != '/':
            parent_path = '/'.join(url_path.rstrip('/').split('/')[:-1])
            if not parent_path:
                parent_path = '/'
            html += f'<tr><td><a href="{parent_path}">../</a></td><td></td></tr>\n'
        
        # Add each item with hit count
        for item in items:
            item_path = os.path.join(directory_path, item)
            item_url = url_path.rstrip('/') + '/' + item
            
            # Get hit count for this file/directory
            if ENABLE_COUNTER_LOCKS:
                # Thread-safe read with lock
                with hits_lock:
                    hits = file_hits.get(item_path, 0)
            else:
                # Naive read without lock (may show inconsistent data)
                hits = file_hits.get(item_path, 0)
            
            # Debug: print what we're looking for
            print(f"Looking up hits for: {item_path}, found: {hits}")
            
            if os.path.isdir(item_path):
                # Directory
                html += f'<tr><td><a href="{item_url}/">{item}/</a></td><td>{hits}</td></tr>\n'
            else:
                # File
                html += f'<tr><td><a href="{item_url}">{item}</a></td><td>{hits}</td></tr>\n'
        
        html += """    </table>
    <hr>
</body>
</html>"""
        
        return html
        
    except Exception as e:
        return f"<html><body><h1>Error generating directory listing</h1><p>{e}</p></body></html>"

def handle_command_line_args():
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

    return serve_directory

def build_file_path(path, serve_directory):
    # Build the file path from the requested path
    if path == '/':
        # Always show directory listing for root path
        file_path = serve_directory
    else:
        # Remove leading and trailing slashes, then join with serve directory
        clean_path = path.strip('/')
        file_path = os.path.join(serve_directory, clean_path)
    
    # Normalize the path to handle different separators
    file_path = os.path.normpath(file_path)
    return file_path

def determine_content_type(file_path):
    # Debug: Check what file_path actually is
    if not isinstance(file_path, str):
        raise TypeError(f"file_path must be str, got {type(file_path)}: {file_path}")
    
    # Get file extension
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
        # Unknown file type - return unsupported type
        content_type = 'text/html'
        response_body = load_template('404_unsupported_type.html')
    
    return content_type, response_body

def handle_request(connectionSocket, addr, serve_directory):
    client_ip = addr[0]  # Extract IP address from address tuple
    
    try:
            # Check rate limit BEFORE processing request
            if not check_rate_limit(client_ip):
                print(f" Blocking request from {client_ip} due to rate limit")
                send_rate_limit_response(connectionSocket)
                connectionSocket.close()
                return
            
            # Receive the HTTP request
            request = connectionSocket.recv(4096).decode()  # Increased buffer size
            print(f"Received request from {client_ip}")
            
            # Simulate 1 second of work (for threading/performance tests)
            # Disable this when testing rate limiting to see the effect clearly
            if ENABLE_PROCESSING_DELAY:
                time.sleep(1)

            # Parse the first line of the request
            if request:
                first_line = request.split('\n')[0]
                method, path, version = first_line.split()
                print(f"Method: {method}, Path: {path}, Version: {version}")

                # Create a simple HTTP response
                file_path = build_file_path(path, serve_directory)
                
                print(f"Looking for: {file_path}")
                
                # ===================================================================
                # COUNTER INCREMENT - Toggle with ENABLE_COUNTER_LOCKS flag
                # ===================================================================
                
                if ENABLE_COUNTER_LOCKS:
                    # THREAD-SAFE VERSION (WITH LOCK - NO RACE CONDITION)
                    with hits_lock:
                        # Critical section - only one thread at a time
                        if file_path not in file_hits:
                            file_hits[file_path] = 0
                        file_hits[file_path] += 1
                        current_hits = file_hits[file_path]
                    
                    print(f"File: {file_path}, Hits: {current_hits}")
                
                else:
                    # NAIVE VERSION (NO LOCK - HAS RACE CONDITION)
                    if file_path not in file_hits:
                        file_hits[file_path] = 0
                    
                    # Add small delay to increase chance of race condition
                    time.sleep(0.001)
                    
                    # Read the current value
                    old_value = file_hits[file_path]
                    
                    # Add another delay between read and write
                    time.sleep(0.001)
                    
                    # Write the new value
                    file_hits[file_path] = old_value + 1
                    
                    print(f"File: {file_path}, Hits: {file_hits[file_path]}")
                
                # ===================================================================
                
                # Check if it's a directory
                if os.path.isdir(file_path):
                    print(f"Directory found: {file_path}")
                    # Generate directory listing
                    directory_html = generate_directory_listing(file_path, path)
                    response_body = directory_html
                    content_type = 'text/html'
                    
                    # Send directory listing response with no-cache headers
                    response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nCache-Control: no-cache, no-store, must-revalidate\r\nPragma: no-cache\r\nExpires: 0\r\nContent-Length: {len(response_body.encode('utf-8'))}\r\n\r\n{response_body}"
                    connectionSocket.send(response.encode('utf-8'))
                    
                # Check if the file exists
                elif os.path.isfile(file_path):
                    # Get file extension and content
                    content_type, response_body = determine_content_type(file_path)

                    # Check if it's an unsupported file type
                    if content_type == 'text/html' and '404' in str(response_body):
                        # Unsupported file type - return 404
                        response = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
                        connectionSocket.send(response.encode())
                    # Create HTTP response for supported files
                    elif isinstance(response_body, str):
                        # Text files (HTML)
                        response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(response_body.encode('utf-8'))}\r\n\r\n{response_body}"
                        connectionSocket.send(response.encode('utf-8'))
                    else:
                        # Binary files (PNG, PDF) - send in chunks
                        response_headers = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(response_body)}\r\n\r\n"
                        connectionSocket.send(response_headers.encode('utf-8'))
                        
                        # Send binary data in chunks
                        chunk_size = 8192  # 8KB chunks
                        for i in range(0, len(response_body), chunk_size):
                            chunk = response_body[i:i + chunk_size]
                            connectionSocket.send(chunk)
                    
                else:
                    # File not found - return 404
                    response_body = load_template('404_not_found.html')
                    response = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
                    connectionSocket.send(response.encode())

    except ConnectionAbortedError as e:
        print(f"Connection aborted by client: {e}")
    except Exception as e:
        print(f"Error: {e}")
        try:
            # Send a simple error response
            error_response = "HTTP/1.1 500 Internal Server Error\r\n\r\nServer Error"
            connectionSocket.send(error_response.encode())
        except:
            print("Could not send error response - connection closed")

    finally:
        # Close the connection
        print("Closing connection")
        try:
            connectionSocket.close()
        except:
            pass


def main():
    serve_directory = handle_command_line_args()

    print(f"Serving files from directory: {serve_directory}")

    serverPort = 8080  # Changed to 8080 (common HTTP port)

    # Create a TCP welcoming socket
    serverSocket = socket(AF_INET, SOCK_STREAM)

    # Allow reusing the address (helpful during development)
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    # Bind the socket to the port
    serverSocket.bind(('', serverPort))

    # Listen for incoming connections (allow up to 20 pending connections)
    serverSocket.listen(20)
    print(f'HTTP Server is ready at http://localhost:{serverPort}')

    # Create a pool of 10 worker threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            connectionSocket, addr = serverSocket.accept()
            print(f"Connection from {addr}")
            
            # Submit work to the thread pool (pass addr for rate limiting)
            executor.submit(handle_request, connectionSocket, addr, serve_directory)


if __name__ == "__main__":
    main()