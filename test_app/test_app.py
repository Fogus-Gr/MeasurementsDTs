import time
import random
import socket
import string

# Simulate CPU load
def cpu_load():
    for _ in range(50000000):  # High CPU load
        _ = random.random() ** 5

# Simulate memory usage
def mem_load():
    # Allocate ~500MB
    data = ['x' * 1000000 for _ in range(500)]
    return data

# Simulate network TX/RX using TCP
def network_load():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('example.com', 80))
            request = "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
            s.sendall(request.encode())
            response = s.recv(8192)
        return len(request), len(response)
    except Exception as e:
        print(f"Network error: {e}")
        return 0, 0

if __name__ == '__main__':
    print("Starting test application...")
    mem_data = mem_load()  # Allocate memory once
    while True:
        cpu_load()  # Generate CPU load
        tx, rx = network_load()  # Generate network activity
        print(f"Sent {tx} bytes, received {rx} bytes")
        time.sleep(0.1)