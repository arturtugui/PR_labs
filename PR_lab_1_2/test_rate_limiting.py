import socket
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

def make_http_request(request_number):
    """Make a single HTTP request and return status code"""
    try:
        # Create a TCP socket
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Connect to the server
        clientSocket.connect(('localhost', 8080))
        
        # Send HTTP GET request
        request = f"GET /index.html HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        clientSocket.send(request.encode())
        
        # Set a timeout
        clientSocket.settimeout(5.0)
        
        # Receive the response (just headers to get status code)
        response = b""
        try:
            chunk = clientSocket.recv(1024)  # Just get the first chunk
            response += chunk
        except socket.timeout:
            pass
        
        clientSocket.close()
        
        # Parse status code
        response_str = response.decode('utf-8', errors='ignore')
        if '200 OK' in response_str:
            return 200
        elif '429' in response_str:
            return 429
        else:
            return 0
        
    except Exception as e:
        print(f"Request #{request_number} failed: {e}")
        return 0

def spam_test(num_requests=10):
    """
    SPAM TEST: Send many requests as fast as possible (above rate limit)
    Expected: First 5 succeed (200), rest get blocked (429)
    """
    print(f"\n{'='*70}")
    print(f"SPAM TEST - Sending requests as fast as possible")
    print(f"{'='*70}")
    print(f"Number of requests: {num_requests}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    # Send all requests concurrently (spam)
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(make_http_request, i+1) for i in range(num_requests)]
        results = [future.result() for future in futures]
    
    total_time = time.time() - start_time
    
    # Count status codes
    status_counter = Counter(results)
    success_count = status_counter.get(200, 0)
    blocked_count = status_counter.get(429, 0)
    failed_count = status_counter.get(0, 0)
    
    print(f"\n{'='*70}")
    print(f"SPAM TEST RESULTS:")
    print(f"{'='*70}")
    print(f"Total requests: {num_requests}")
    print(f"Successful (200 OK): {success_count}")
    print(f"Blocked (429): {blocked_count}")
    print(f"Failed/Errors: {failed_count}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"{'='*70}\n")
    
    return success_count, blocked_count, total_time

def normal_test(num_requests=10, requests_per_second=4):
    """
    NORMAL TEST: Send requests at controlled rate (below limit)
    Expected: All requests succeed (200 OK)
    """
    print(f"\n{'='*70}")
    print(f"NORMAL USER TEST - Sending requests at controlled rate")
    print(f"{'='*70}")
    print(f"Number of requests: {num_requests}")
    print(f"Rate: {requests_per_second} requests/second (below 5/sec limit)")
    print(f"{'='*70}\n")
    
    delay = 1.0 / requests_per_second  # Delay between requests
    start_time = time.time()
    results = []
    
    for i in range(num_requests):
        result = make_http_request(i+1)
        results.append(result)
        if i < num_requests - 1:  # Don't sleep after last request
            time.sleep(delay)
    
    total_time = time.time() - start_time
    
    # Count status codes
    status_counter = Counter(results)
    success_count = status_counter.get(200, 0)
    blocked_count = status_counter.get(429, 0)
    failed_count = status_counter.get(0, 0)
    
    print(f"\n{'='*70}")
    print(f"NORMAL USER TEST RESULTS:")
    print(f"{'='*70}")
    print(f"Total requests: {num_requests}")
    print(f"Successful (200 OK): {success_count}")
    print(f"Blocked (429): {blocked_count}")
    print(f"Failed/Errors: {failed_count}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"{'='*70}\n")
    
    return success_count, blocked_count, total_time

def comparison_test():
    print("\n" + "="*70)
    print("RATE LIMITING COMPARISON TEST")
    print("="*70)
    print("\nMake sure your server is running at http://localhost:8080")
    print("with ENABLE_RATE_LIMITING = True")
    print("Starting tests...\n")
    
    # Test 1: Spam (above limit)
    spam_success, spam_blocked, spam_time = spam_test(num_requests=10)
    
    time.sleep(2)
    
    # Test 2: Normal (below limit)
    normal_success, normal_blocked, normal_time = normal_test(num_requests=10, requests_per_second=4)
    
    # Final comparison
    print("\n" + "="*70)
    print("FINAL COMPARISON")
    print("="*70)
    print(f"\nSPAMMER (20 requests, as fast as possible):")
    print(f"  Successful: {spam_success}")
    print(f"  Blocked: {spam_blocked}")
    print(f"  Throughput: {spam_success / spam_time:.2f} successful requests/sec")
    print(f"\nNORMAL USER (20 requests, 4/sec rate):")
    print(f"  Successful: {normal_success}")
    print(f"  Blocked: {normal_blocked}")
    print(f"  Throughput: {normal_success / normal_time:.2f} successful requests/sec")
    print(f"\n{'='*70}")
    print(f"THROUGHPUT COMPARISON:")
    print(f"  Spammer: {spam_success / spam_time:.2f} requests/sec (capped by rate limit)")
    print(f"  Normal:  {normal_success / normal_time:.2f} requests/sec (natural rate)")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    comparison_test()
