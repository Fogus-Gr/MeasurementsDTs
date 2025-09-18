import time
import statistics
from collections import deque
from datetime import datetime
import csv
import os

class PoseMonitor:
    def __init__(self, window_size=30, log_file='pose_metrics.csv'):
        """
        Monitor for pose estimation metrics.
        
        Args:
            window_size (int): Number of samples to keep for moving statistics
            log_file (str): Path to CSV file for logging metrics
        """
        self.window_size = window_size
        self.log_file = log_file
        
        # Initialize deques for moving statistics
        self.fps_history = deque(maxlen=window_size)
        self.x_history = deque(maxlen=window_size)
        self.y_history = deque(maxlen=window_size)
        
        # Initialize counters
        self.frame_count = 0
        self.last_update_time = time.time()
        self.start_time = time.time()
        
        # Initialize CSV log file
        self._init_log_file()
    
    def _init_log_file(self):
        """Initialize the CSV log file with headers if it doesn't exist."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'fps_avg', 'fps_min', 'fps_max', 'fps_std',
                    'x_avg', 'x_min', 'x_max', 'x_std',
                    'y_avg', 'y_min', 'y_max', 'y_std',
                    'frame_count'
                ])
    
    def update(self, keypoints=None):
        """
        Update the monitor with new frame data.
        
        Args:
            keypoints: List of keypoints from pose estimation model
        """
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        
        # Calculate FPS
        if elapsed > 0:
            fps = 1.0 / elapsed
            self.fps_history.append(fps)
        
        # Process keypoints if available
        if keypoints is not None and len(keypoints) > 0:
            # Get first person's keypoints (assuming batch size 1 for now)
            person_keypoints = keypoints[0]
            
            # Calculate center of mass (average x, y)
            if len(person_keypoints) > 0:
                valid_points = [kp for kp in person_keypoints if kp[2] > 0.2]  # Confidence threshold
                if valid_points:
                    avg_x = sum(kp[0] for kp in valid_points) / len(valid_points)
                    avg_y = sum(kp[1] for kp in valid_points) / len(valid_points)
                    self.x_history.append(avg_x)
                    self.y_history.append(avg_y)
        
        # Log statistics every second
        if current_time - self.start_time >= 1.0:
            self._log_metrics(current_time)
            self.start_time = current_time
            self.frame_count = 0
        
        self.last_update_time = current_time
        self.frame_count += 1
    
    def _log_metrics(self, timestamp):
        """Calculate and log metrics to CSV."""
        # Calculate FPS statistics
        fps_stats = self._calculate_stats(self.fps_history)
        
        # Calculate X-coordinate statistics
        x_stats = self._calculate_stats(self.x_history)
        
        # Calculate Y-coordinate statistics
        y_stats = self._calculate_stats(self.y_history)
        
        # Write to CSV
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                fps_stats.get('avg', 0), fps_stats.get('min', 0), 
                fps_stats.get('max', 0), fps_stats.get('std', 0),
                x_stats.get('avg', 0), x_stats.get('min', 0), 
                x_stats.get('max', 0), x_stats.get('std', 0),
                y_stats.get('avg', 0), y_stats.get('min', 0), 
                y_stats.get('max', 0), y_stats.get('std', 0),
                self.frame_count
            ])
    
    @staticmethod
    def _calculate_stats(values):
        """Calculate statistics for a list of values."""
        if not values:
            return {'avg': 0, 'min': 0, 'max': 0, 'std': 0}
        
        return {
            'avg': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def get_current_metrics(self):
        """Get current metrics as a dictionary."""
        return {
            'fps': self._calculate_stats(self.fps_history),
            'x': self._calculate_stats(self.x_history),
            'y': self._calculate_stats(self.y_history),
            'frame_count': self.frame_count
        }
    
    def print_metrics(self):
        """Print current metrics to console."""
        metrics = self.get_current_metrics()
        
        print("\n=== Current Pose Estimation Metrics ===")
        print(f"FPS: {metrics['fps']['avg']:.1f} (min: {metrics['fps']['min']:.1f}, "
              f"max: {metrics['fps']['max']:.1f}, std: {metrics['fps']['std']:.1f})")
        
        if self.x_history:
            print(f"X-Coord: {metrics['x']['avg']:.1f} (min: {metrics['x']['min']:.1f}, "
                  f"max: {metrics['x']['max']:.1f}, std: {metrics['x']['std']:.1f})")
        
        if self.y_history:
            print(f"Y-Coord: {metrics['y']['avg']:.1f} (min: {metrics['y']['min']:.1f}, "
                  f"max: {metrics['y']['max']:.1f}, std: {metrics['y']['std']:.1f})")
        
        print(f"Frames processed: {self.frame_count}")
        print("=" * 40)
