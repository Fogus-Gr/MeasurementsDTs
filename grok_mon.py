import threading
import time
import csv
import psutil
import pynvml

def monitor(stop_event, csv_file):
    p = psutil.Process()  # Monitor the current process
    pynvml.nvmlInit()  # Initialize NVIDIA Management Library
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # GPU index 0
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'cpu_percent', 'memory_usage_mb', 'gpu_util_percent', 'gpu_mem_util_percent'])
        while not stop_event.is_set():
            cpu_percent = p.cpu_percent(interval=0.5)  # Measure over 500ms
            memory_usage = p.memory_info().rss / (1024 * 1024)  # Convert bytes to MB
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util = utilization.gpu  # GPU compute utilization (%)
            gpu_mem_util = utilization.memory  # GPU memory utilization (%)
            timestamp = time.time()
            writer.writerow([timestamp, cpu_percent, memory_usage, gpu_util, gpu_mem_util])
    pynvml.nvmlShutdown()

if __name__ == '__main__':
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor, args=(stop_event, 'metrics.csv'))
    monitor_thread.start()
    
    # Your AlphaPose code goes here
    # For example:
    # import alphapose
    # ... (run your AlphaPose script)
    
    stop_event.set()  # Signal monitoring thread to stop
    monitor_thread.join()  # Wait for monitoring thread to finish
