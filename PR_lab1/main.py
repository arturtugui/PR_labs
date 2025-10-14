from socket import *

# Step 1: Create a TCP socket
serverPort = 12000
serverSocket = socket(AF_INET, SOCK_STREAM)

# Step 2: Bind to all available interfaces on port 12000
serverSocket.bind(('', serverPort))

# Step 3: Start listening (max 1 queued connection)
serverSocket.listen(1)
print("The server is ready to receive HTTP requests on port", serverPort)

# Step 4: Infinite loop to handle multiple browser requests
while True:
    # Wait for a connection from a client (e.g., a browser)
    connectionSocket, addr = serverSocket.accept()
    print(f"Connected to client: {addr}")

    try:
        # Step 5: Receive the HTTP request (from browser)
        request = connectionSocket.recv(1024).decode()
        print("Received request:")
        print(request)

        # Optional: Extract the first line (the HTTP request line)
        request_line = request.splitlines()[0] if request else ""
        print("Request line:", request_line)

        # Step 6: Build a valid HTTP response
        response_body = "<html><body><h1>Hello from Python TCP Server!</h1></body></html>"
        response_headers = "HTTP/1.1 200 OK\r\n" \
                           "Content-Type: text/html\r\n" \
                           f"Content-Length: {len(response_body)}\r\n" \
                           "Connection: close\r\n\r\n"

        # Step 7: Send headers + body as response
        full_response = response_headers + response_body
        connectionSocket.send(full_response.encode())

    except Exception as e:
        print("Error:", e)

    finally:
        # Step 8: Close the connection socket (but not the main server socket)
        connectionSocket.close()
        print("Connection closed.\n")
