from socket import *
import os

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
        print(request)
        print("-" * 40)

        # Parse the first line of the request
        if request:
            first_line = request.split('\n')[0]
            method, path, version = first_line.split()
            print(f"Method: {method}, Path: {path}, Version: {version}")

            # Create a simple HTTP response
            if path == '/':
                # Serve a simple HTML page
                response_body = """
                <html>
                <head><title>My First HTTP Server</title></head>
                <body>
                    <h1>Hello from my HTTP Server!</h1>
                    <p>This is working! 🎉</p>
                    <p>You successfully converted TCP to HTTP!</p>
                </body>
                </html>
                """
                
                # HTTP response with headers
                response = f"""HTTP/1.1 200 OK\r
Content-Type: text/html\r
Content-Length: {len(response_body)}\r
\r
{response_body}"""

            else:
                # For any other path, return 404
                response_body = """
                <html>
                <head><title>404 Not Found</title></head>
                <body>
                    <h1>404 - File Not Found</h1>
                    <p>The requested file was not found on this server.</p>
                </body>
                </html>
                """
                
                response = f"""HTTP/1.1 404 Not Found\r
Content-Type: text/html\r
Content-Length: {len(response_body)}\r
\r
{response_body}"""

            # Send the response
            connectionSocket.send(response.encode())

    except Exception as e:
        print(f"Error: {e}")
        # Send a simple error response
        error_response = "HTTP/1.1 500 Internal Server Error\r\n\r\nServer Error"
        connectionSocket.send(error_response.encode())

    finally:
        # Close the connection
        connectionSocket.close()