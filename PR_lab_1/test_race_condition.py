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
    print(f"{'='*70}")
    print(f"\n⚠️  WITH RACE CONDITION (current implementation):")
    print(f"   The hit count shown will likely be LESS than {num_requests}")
    print(f"\n✅ WITHOUT RACE CONDITION (after adding lock):")
    print(f"   The hit count shown will be EXACTLY {num_requests}")
    print(f"{'='*70}\n")

def run_multiple_tests():
    """Run multiple tests to show inconsistency"""
    print("\n" + "="*70)
    print("RUNNING MULTIPLE TESTS TO SHOW INCONSISTENCY")
    print("="*70)
    print("We'll make the same request multiple times.")
    print("If there's a race condition, the counts will be inconsistent.\n")
    
    for test_num in range(1, 4):
        print(f"\n--- Test Run #{test_num} ---")
        test_race_condition(num_requests=30, target_file="/index.html")
        
        if test_num < 3:
            print("\nWaiting 2 seconds before next test...\n")
            time.sleep(2)

if __name__ == "__main__":
    print("\n" + "="*70)
    print("HTTP SERVER RACE CONDITION DEMONSTRATION")
    print("="*70)
    print("\nMake sure your server is running with:")
    print("  python http_server_basic.py ./website")
    print("\nThis test will:")
    print("  1. Make many concurrent requests to the same file")
    print("  2. Show that the hit counter has a race condition")
    print("  3. The final count will be LESS than expected")
    print("\nPress Enter to start testing...")
    input()
    
    # Run a single test
    test_race_condition(num_requests=50, target_file="/index.html")
    
    print("\nWould you like to run multiple tests to see inconsistency? (y/n): ", end="")
    choice = input().lower()
    
    if choice == 'y':
        run_multiple_tests()
