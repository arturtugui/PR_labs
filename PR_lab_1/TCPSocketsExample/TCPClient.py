from socket import *

serverName = 'localhost'  # or replace with actual server name/IP
serverPort = 12000

# Create a TCP socket
clientSocket = socket(AF_INET, SOCK_STREAM)

# Connect to the server
clientSocket.connect((serverName, serverPort))

# Get user input
sentence = input('Input lowercase sentence: ')

# Send the input to the server
clientSocket.send(sentence.encode())

# Receive the modified sentence from the server
modifiedSentence = clientSocket.recv(1024)

print('From Server:', modifiedSentence.decode())

# Close the connection
clientSocket.close()
