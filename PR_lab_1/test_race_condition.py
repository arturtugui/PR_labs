import socket
import time
from concurrent.futures import ThreadPoolExecutor

def make_http_request(request_number, target_file="/documents/climate_change/report-pages.pdf"):
    """Make a single HTTP request"""
    try:
        # Create a TCP socket
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Connect to the server
        clientSocket.connect(('localhost', 8080))
        
        # Send HTTP GET request
        request = f"GET {target_file} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        clientSocket.send(request.encode())
        
        # Set a timeout
        clientSocket.settimeout(5.0)
        
        # Receive the complete response
        response = b""
        try:
            while True:
                chunk = clientSocket.recv(4096)
                if not chunk:
                    break
                response += chunk
        except socket.timeout:
            pass
        
        clientSocket.close()
        return True
        
    except Exception as e:
        print(f"Request #{request_number} failed: {e}")
        return False

def test_race_condition(num_requests=50, target_file="/index.html"):
    """
    Test the server to demonstrate race condition.
    
    With race condition: final count will be LESS than num_requests
    Without race condition: final count will EQUAL num_requests
    """
    print(f"\n{'='*70}")
    print(f"RACE CONDITION TEST")
    print(f"{'='*70}")
    print(f"Target file: {target_file}")
    print(f"Number of concurrent requests: {num_requests}")
    print(f"Expected hit count: {num_requests}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    # Make concurrent requests using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        # Submit all requests at once to maximize race condition
        futures = [executor.submit(make_http_request, i+1, target_file) for i in range(num_requests)]
        
        # Wait for all to complete
        results = [future.result() for future in futures]
    
    total_time = time.time() - start_time
    successful = sum(1 for r in results if r)
    
    print(f"\nTest completed in {total_time:.2f} seconds")
    print(f"Successful requests: {successful}/{num_requests}")
    print(f"\n{'='*70}")
    print(f"Now check the directory listing at http://localhost:8080/")
    print(f"to see the actual hit count for '{target_file}'")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("HTTP SERVER RACE CONDITION DEMONSTRATION")
    print("="*70)
    print("\nMake sure your server is running at http://localhost:8080")
    print("Starting test...\n")
    
    # Run a single test
    test_race_condition(num_requests=50, target_file="/index.html")
    
    print("\nHINT: Check the hit count in the directory listing at:")
    print("      http://localhost:8080/")
    print("\nIf ENABLE_COUNTER_LOCKS = False: count will be < 50 (race condition)")
    print("If ENABLE_COUNTER_LOCKS = True:  count will be = 50 (thread-safe)\n")
