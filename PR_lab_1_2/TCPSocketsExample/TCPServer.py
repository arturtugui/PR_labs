from socket import *

serverPort = 12000

# Create a TCP welcoming socket
serverSocket = socket(AF_INET, SOCK_STREAM)

# Bind the socket to the port
serverSocket.bind(('', serverPort))

# Listen for incoming connections (backlog = 1)
serverSocket.listen(1)
print('The server is ready to receive')

while True:
    # Accept a new connection
    connectionSocket, addr = serverSocket.accept()

    # Receive data from the client
    sentence = connectionSocket.recv(1024).decode()

    # Convert to uppercase
    capitalizedSentence = sentence.upper()

    # Send the result back to the client
    connectionSocket.send(capitalizedSentence.encode())

    # Close the connection
    connectionSocket.close()