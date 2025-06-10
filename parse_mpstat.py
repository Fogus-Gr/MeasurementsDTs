import subprocess
import pandas as pd
from datetime import datetime

def parse_mpstat_output():
    times = []
    timestamps = []
    cpu_usages = []
    try:
        # Run mpstat to get CPU usage statistics with 0.5s interval
        print("Running mpstat...")
        result = subprocess.run(['sudo', 'mpstat', '-P', 'ALL', '1', '120'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"mpstat command failed with error: {result.stderr}")
            return times, timestamps, cpu_usages
            
        # Save the output to a file
        with open('cpu_usage.txt', 'w') as f:
            f.write(result.stdout)
            print("Saved mpstat output to file")
        
        # Read the mpstat output and process it
        with open('cpu_usage.txt', 'r') as f:
            lines = f.readlines()
            print(f"Read {len(lines)} lines from file")
        
        # Process the data manually since the format is complex
        start_time = None
        for line in lines:
            if 'CPU' in line or 'Average' in line:
                continue
            
            parts = line.split()
            if len(parts) >= 3 and parts[1] == 'all':
                if start_time is None:
                    start_time = datetime.strptime(parts[0], '%H:%M:%S')
                current_time = datetime.strptime(parts[0], '%H:%M:%S')
                time_diff = (current_time - start_time).total_seconds()
                timestamps.append(parts[0])
                times.append(time_diff)
                cpu_usages.append(float(parts[2]))  # %usr column (column index 2)
        
        print(f"Collected {len(times)} data points")
        return times, timestamps, cpu_usages
    except Exception as e:
        print(f"Error processing CPU usage data {str(e)}")
        return times, timestamps, cpu_usages
    
    return times, timestamps, cpu_usages
        
if __name__ == "__main__":
    try:
        times, timestamps, cpu_usages = parse_mpstat_output()
        if times and cpu_usages:
            print("Successfully parsed CPU usage data")
            print(f"Number of data points: {len(times)}")
            
            # Create DataFrame and export to CSV
            data = {'Time (s)': times,
                    'Timestamp': timestamps,
                    'CPU Usage (%)': cpu_usages}
            df = pd.DataFrame(data)
            df.to_csv('cpu_usage.csv', index=False)
            print(f"\nData exported to cpu_usage.csv")
            
            # Print the first few rows
            print("\nFirst few rows of data:")
            print(df.head())
        else:
            print("No data was collected")
    except Exception as e:
        print(f"Error processing CPU usage data {str(e)}")
        if 'times' in locals():
            print(f"Number of data points: {len(times)}")
        else:
            print("No data points collected")
    except Exception as e:
        print(f"Error processing CPU usage data: {str(e)}")
        print(f"Number of data points: {len(times)}")