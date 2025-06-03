import time
import random
import socket
import threading

# Simulate CPU load
def cpu_load():
    for _ in range(50000000):
        _ = random.random() ** 5

# Simulate memory usage
def mem_load():
    data = ['x' * 1000000 for _ in range(500)]
    return data

# Simulate heavy network TX/RX using TCP
def network_load(num_requests=20):
    tx_total = 0
    rx_total = 0

    def single_request():
        nonlocal tx_total, rx_total
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('example.com', 80))
                request = "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
                s.sendall(request.encode())
                response = s.recv(65536)  # Try to read more data
                tx, rx = len(request), len(response)
                # Accumulate totals in a thread-safe way
                lock.acquire()
                tx_total += tx
                rx_total += rx
                lock.release()
        except Exception as e:
            pass  # Ignore errors for speed

    threads = []
    lock = threading.Lock()
    for _ in range(num_requests):
        t = threading.Thread(target=single_request)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    return tx_total, rx_total

if __name__ == '__main__':
    print("Starting test application...")
    mem_data = mem_load()
    while True:
        cpu_load()
        tx, rx = network_load(num_requests=20)  # 20 parallel requests per loop
        print(f"Sent {tx} bytes, received {rx} bytes")
        time.sleep(0.05)  # Reduce sleep for more traffic