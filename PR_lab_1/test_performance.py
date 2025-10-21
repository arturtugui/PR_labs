import socket
import time
from concurrent.futures import ThreadPoolExecutor

def make_http_request(request_number):
    """Make a single HTTP request and measure the time"""
    try:
        start_time = time.time()
        
        # Create a TCP socket
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Connect to the server
        clientSocket.connect(('localhost', 8080))
        
        # Send HTTP GET request
        request = "GET /index.html HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        clientSocket.send(request.encode())
        
        # Set a timeout to avoid hanging forever
        clientSocket.settimeout(5.0)
        
        # Receive the complete response
        response = b""
        try:
            while True:
                chunk = clientSocket.recv(4096)
                if not chunk:
                    # Server closed connection, we got everything
                    break
                response += chunk
        except socket.timeout:
            print(f"Request #{request_number} timed out")
        
        clientSocket.close()
        
        elapsed_time = time.time() - start_time
        print(f"Request #{request_number} completed in {elapsed_time:.2f} seconds")
        
        return elapsed_time
        
    except Exception as e:
        print(f"Request #{request_number} failed: {e}")
        return None

def test_concurrent_requests(num_requests=10):
    """Test the server with concurrent requests"""
    print(f"\n{'='*60}")
    print(f"Testing with {num_requests} CONCURRENT requests")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    # Make concurrent requests using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        # Submit all requests at once
        futures = [executor.submit(make_http_request, i+1) for i in range(num_requests)]
        
        # Wait for all to complete and collect results
        times = [future.result() for future in futures]
    
    total_time = time.time() - start_time
    
    # Filter out failed requests
    successful_times = [t for t in times if t is not None]
    
    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"{'='*60}")
    print(f"Total requests: {num_requests}")
    print(f"Successful: {len(successful_times)}")
    print(f"Failed: {num_requests - len(successful_times)}")
    print(f"\nTotal time: {total_time:.2f} seconds")
    
    if successful_times:
        print(f"Average time per request: {sum(successful_times)/len(successful_times):.2f} seconds")
        print(f"Fastest request: {min(successful_times):.2f} seconds")
        print(f"Slowest request: {max(successful_times):.2f} seconds")

    print(f"{'='*60}\n")
    return total_time

def test_sequential_requests(num_requests=10):
    """Test the server with sequential requests (for comparison)"""
    print(f"\n{'='*60}")
    print(f"Testing with {num_requests} SEQUENTIAL requests")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    times = []
    
    for i in range(num_requests):
        elapsed = make_http_request(i+1)
        if elapsed:
            times.append(elapsed)
    
    total_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"{'='*60}")
    print(f"Total requests: {num_requests}")
    print(f"Successful: {len(times)}")
    print(f"Failed: {num_requests - len(times)}")
    print(f"\nTotal time: {total_time:.2f} seconds")
    
    if times:
        print(f"Average time per request: {sum(times)/len(times):.2f} seconds")
    
    print(f"{'='*60}\n")
    return total_time

if __name__ == "__main__":
    print("\n" + "="*60)
    print("HTTP SERVER PERFORMANCE TEST")
    print("="*60)
    print("\nMake sure your server is running with:")
    print("  python http_server_basic.py ./website")
    print("\nPress Enter to start testing...")
    input()
    
    # Test concurrent requests (should be fast with multithreading)
    concurrent_time = test_concurrent_requests(10)
    
    print("\nWould you like to test sequential requests too? (y/n): ", end="")
    choice = input().lower()
    
    if choice == 'y':
        sequential_time = test_sequential_requests(10)

    print("\nSUMMARY:")
    print(f"Concurrent time: {concurrent_time:.2f} seconds")
    print(f"Sequential time: {sequential_time:.2f} seconds")
