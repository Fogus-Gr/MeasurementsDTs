import csv

def parse_traffic_data(file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Attaching") or line.startswith("Tracing"):
                continue
            # Expecting: timestamp,Type,PID,Command,Bytes
            parts = line.split(',')
            if len(parts) == 5 and "iperf" in parts[3].lower():
                data.append(parts)

    with open('traffic_report.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Timestamp', 'Type', 'PID', 'Command', 'Bytes'])
        if data:
            writer.writerows(data)
        else:
            print("No data captured to write to CSV.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        parse_traffic_data(sys.argv[1])
    else:
        parse_traffic_data('output/traffic_data.txt')