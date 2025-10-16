#!/usr/bin/env python3
"""
HPE Log Parser - Parse structured logs for analysis
"""

import json
import pandas as pd
from datetime import datetime
import argparse
import os

def parse_structured_logs(log_file='hpe_structured.log'):
    """Parse structured logs and return DataFrame"""
    if not os.path.exists(log_file):
        print(f"Log file {log_file} not found")
        return None
    
    events = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                events.append(event)
            except json.JSONDecodeError:
                continue
    
    if not events:
        print("No valid events found in log file")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(events)
    return df

def analyze_performance(df):
    """Analyze performance data from logs"""
    if df is None:
        return
    
    # Filter performance summaries
    perf_data = df[df['event_type'] == 'performance_summary']
    
    if perf_data.empty:
        print("No performance data found")
        return
    
    print("=== PERFORMANCE ANALYSIS ===")
    for _, row in perf_data.iterrows():
        data = row['data']
        print(f"\nModel: {data.get('model_type', 'unknown')}")
        print(f"Input: {data.get('input_source', 'unknown')}")
        print(f"Total Frames: {data.get('total_frames', 0)}")
        print(f"Average FPS: {data.get('fps_avg', 0):.2f}")
        print(f"Inference Time: {data.get('inference_time_avg', 0):.2f}ms")
        print(f"Timestamp: {row['timestamp']}")

def analyze_sessions(df):
    """Analyze session data from logs"""
    if df is None:
        return
    
    # Filter session events
    sessions = df[df['event_type'].isin(['session_start', 'session_end'])]
    
    if sessions.empty:
        print("No session data found")
        return
    
    print("\n=== SESSION ANALYSIS ===")
    for _, row in sessions.iterrows():
        data = row['data']
        event_type = row['event_type']
        print(f"\n{event_type.upper()}:")
        print(f"  Method: {data.get('method', 'unknown')}")
        print(f"  Input: {data.get('input', 'unknown')}")
        print(f"  Device: {data.get('device', 'unknown')}")
        if event_type == 'session_start':
            print(f"  Timeout: {data.get('timeout', 'N/A')}")
            print(f"  Max Frames: {data.get('max_frames', 'N/A')}")
        print(f"  Timestamp: {row['timestamp']}")

def analyze_video_properties(df):
    """Analyze video properties from logs"""
    if df is None:
        return
    
    # Filter video properties
    video_data = df[df['event_type'] == 'video_properties_detected']
    
    if video_data.empty:
        print("No video properties data found")
        return
    
    print("\n=== VIDEO PROPERTIES ANALYSIS ===")
    for _, row in video_data.iterrows():
        data = row['data']
        print(f"\nInput: {data.get('input_url', 'unknown')}")
        print(f"  FPS: {data.get('fps', 0):.2f}")
        print(f"  Duration: {data.get('duration', 0):.1f}s")
        print(f"  Total Frames: {data.get('total_frames', 0)}")
        print(f"  Timestamp: {row['timestamp']}")

def export_to_csv(df, output_file='hpe_analysis.csv'):
    """Export analysis to CSV"""
    if df is None:
        return
    
    # Flatten nested data for CSV export
    flattened_data = []
    for _, row in df.iterrows():
        flat_row = {
            'timestamp': row['timestamp'],
            'event_type': row['event_type']
        }
        flat_row.update(row['data'])
        flattened_data.append(flat_row)
    
    flat_df = pd.DataFrame(flattened_data)
    flat_df.to_csv(output_file, index=False)
    print(f"\nData exported to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Parse HPE structured logs')
    parser.add_argument('--log-file', default='hpe_structured.log', help='Path to structured log file')
    parser.add_argument('--export-csv', help='Export to CSV file')
    parser.add_argument('--show-performance', action='store_true', help='Show performance analysis')
    parser.add_argument('--show-sessions', action='store_true', help='Show session analysis')
    parser.add_argument('--show-video', action='store_true', help='Show video properties analysis')
    parser.add_argument('--show-all', action='store_true', help='Show all analyses')
    
    args = parser.parse_args()
    
    # Parse logs
    df = parse_structured_logs(args.log_file)
    
    if df is None:
        return
    
    # Show analyses
    if args.show_all or args.show_performance:
        analyze_performance(df)
    
    if args.show_all or args.show_sessions:
        analyze_sessions(df)
    
    if args.show_all or args.show_video:
        analyze_video_properties(df)
    
    # Export if requested
    if args.export_csv:
        export_to_csv(df, args.export_csv)

if __name__ == '__main__':
    main()
