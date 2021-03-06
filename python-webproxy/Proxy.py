# Include the libraries for socket and system calls
import socket
import sys
import os
import argparse
import re

# 1MB buffer size
BUFFER_SIZE = 1000000

parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()

# Create a server socket, bind it to a port and start listening
port = int(args.port)

try:
  # Create a server socket
  
  serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  
  print 'Connected socket'
except:
  print 'Failed to create socket'
  sys.exit()

try:
  # Bind the the server socket to a host and port
  
  serverSocket.bind(('',port))
  
  print 'Port is bound'
except:
  print('Port is in use')
  sys.exit()

try:
  # Listen on the server socket
  
  serverSocket.listen(3) # maximum connections in queue
  
  print 'Listening to socket'
except:
  print 'Failed to listen'
  sys.exit()

while True:
  print 'Waiting connection...'

  clientSocket = None
  try:
    # Accept connection from client and store in the clientSocket
    
    clientSocket, clientAddress = serverSocket.accept()
    
    print 'Received a connection from:', args.hostname
  except:
    print 'Failed to accept connection'
    sys.exit()

  message = 'METHOD URI VERSION'
  # Get request from client
  # and store it in message
  
  message = clientSocket.recv(BUFFER_SIZE)
  
  print 'Received request:'
  print '< ' + message

  # Extract the parts of the HTTP request line from the given message
  requestParts = message.split()
  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]

  print 'Method:\t\t' + method
  print 'URI:\t\t' + URI
  print 'Version:\t' + version
  print ''

  # Remove http protocol from the URI
  URI = re.sub('^(/?)http(s?)://', '', URI, 1)

  # Remove parent directory changes - security
  URI = URI.replace('/..', '')

  # Split hostname from resource
  resourceParts = URI.split('/', 1)
  hostname = resourceParts[0]
  resource = '/'

  if len(resourceParts) == 2:
    # Resource is absolute URI with hostname and resource
    resource = resource + resourceParts[1]

  print 'Requested Resource:\t' + resource

  cacheLocation = './' + hostname + resource
  if cacheLocation.endswith('/'):
    cacheLocation = cacheLocation + 'default'

  print 'Cache location:\t\t' + cacheLocation

  fileExists = os.path.isfile(cacheLocation)
  
  try:
    # Check wether the file exist in the cache
    cacheFile = open(cacheLocation, "r")
    outputdata = cacheFile.readlines()

    print 'Cache hit! Loading from cache file: ' + cacheLocation
    # ProxyServer finds a cache hit
    # Send back contents of cached file
    
    for line in outputdata:
      clientSocket.send(line)
    
    cacheFile.close()

  # Error handling for file not found in cache
  except IOError:
    if fileExists:
      clientResponse = ''
      # If we get here, the file exists but the proxy can't open or read it
      # store the value in clientResponse
      
      clientResponse = "HTTP/1.1 500 Internal Server Error\r\n Can\'t Read Document"

      print 'Sending to the client:'
      print '> ' + clientResponse
      print '>'
      clientSocket.sendall(clientResponse + "\r\n\r\n")

    else:
      originServerSocket = None
      # Create a socket to connect to origin server
      # and store in originServerSocket
      
      originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      
      print 'Connecting to:\t\t' + hostname + '\n'
      try:
        # Get the IP address for a hostname
        address = socket.gethostbyname(hostname)

        # Connect to the origin server
        
        originServerSocket.connect((address, 80))
        
        print 'Connected to origin Server'

        # Create a file object associated with this socket
        # This lets us use file function calls
        originServerFileObj = originServerSocket.makefile('+', 0)

        originServerRequest = ''
        originServerRequestHeader = ''
        # Create origin server request line and headers to send
        # and store in originServerRequestHeader and originServerRequest
        # originServerRequest is the first line in the request and
        # originServerRequestHeader is the second line in the request
        
        originServerRequest = "GET" + " " + resource + " " + "HTTP/1.1"
        originServerRequestHeader = "\r\n".join(
          ["Accept:*/*", "Accept-Language:*",
          "Accept-Charset: utf-8",
          "Accept-Encoding:*",
          "From: karan.sethi@student.adelaide.edu.au",
          "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
          "Host: {}".format(args.hostname)])
        
        # Construct the request to send to the origin server
        request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'

        # Request the web resource from origin server
        print 'Forwarding request to origin server:'
        for line in request.split('\r\n'):
          print '> ' + line

        try:
          originServerSocket.sendall(request)
        except socket.error:
          print 'Send failed'
          sys.exit()

        originServerFileObj.write(request)

        # Get the response from the origin server
        
        originResponse = ''
        originResponse = originServerSocket.recv(BUFFER_SIZE)
        
        # Send the response to the client
        
        clientSocket.sendall(originResponse + "\r\n\r\n")
        
        # finished sending to origin server - shutdown socket writes
        originServerSocket.shutdown(socket.SHUT_WR)

        print 'Request sent to origin server\n'

        # Create a new file in the cache for the requested file.
        # Also send the response in the buffer to client socket
        # and the corresponding file in the cache
        cacheDir, file = os.path.split(cacheLocation)
        print 'cached directory ' + cacheDir
        if not os.path.exists(cacheDir):
          os.makedirs(cacheDir)
        cacheFile = open(cacheLocation, 'wb')

        # Save origin server response in the cache file
        
        cacheFile.write(originResponse)
        
        print 'done sending'
        originServerSocket.close()
        cacheFile.close()
        print 'cache file closed'
        clientSocket.shutdown(socket.SHUT_WR)
        print 'client socket shutdown for writing'
      except IOError, (value, message):
        print 'origin server request failed. ' + message

  try:
    clientSocket.close()
  except:
    print 'Failed to close client socket'
