#!/usr/bin/env python3
"""
Simple test to verify OpenVINO functionality without async complications
"""

import sys
import os
import cv2
import torch
import time

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable OpenCV debug output
cv2.setLogLevel(0)  # 0=DEBUG, 1=INFO, 2=WARN, 3=ERROR, 4=SILENT

from openvino_base_hpe import OpenVINOBaseHPE

def list_available_cameras():
    """List available cameras"""
    print("Checking available cameras...")
    for i in range(5):  # Check first 5 camera indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"Camera {i}: {frame.shape} - Working")
            else:
                print(f"Camera {i}: Connected but no frame")
            cap.release()
        else:
            print(f"Camera {i}: Not available")
    print()

def test_sync_webcam():
    """Test synchronous webcam processing"""
    print("Testing Synchronous OpenVINO HPE with webcam...")
    print("=" * 50)
    
    # List available cameras first
    list_available_cameras()

    # Create synchronous HPE instance with model defaults
    hpe = OpenVINOBaseHPE(
        model_type="efficienthrnet1",  # Use EfficientHRNet model
        device="CPU",
        input_src="2",  # FaceTime HD Camera (index 2)
        # Let the model use its own defaults for:
        # - ov_threads (will use model's default)
        # - ov_mode (will use model's default) 
        # - score_thresh (will use model's default)
        save_image=False  # We'll handle display ourselves
    )
    
    # Bitrate monitoring variables
    bitrate_samples = []
    last_bitrate_time = time.time()

    print("Configuration:")
    print(f"  Model: {hpe.model_type}")
    print(f"  Device: {hpe.device}")
    print(f"  Threads: {hpe.ov_threads} (model default)")
    print(f"  Mode: {hpe.ov_mode} (model default)")
    print(f"  Score Threshold: {hpe.score_thresh} (model default)")
    print()

    print("Starting synchronous processing...")
    print("Controls:")
    print("  - Press 'q' to quit")
    print("  - Press Ctrl+C to stop")
    print()
    print("💡 Note: Camera access happens during initialization.")
    print("   The green light may appear when video window opens.")
    print()

    # Test camera access with retry
    print("Testing camera access...")
    if hpe.cap is not None and hpe.cap.isOpened():
        # Give camera time to warm up
        
        time.sleep(0.5)

        # Try multiple times to get a frame
        max_attempts = 3
        for attempt in range(max_attempts):
            ret, test_frame = hpe.cap.read()
            if ret and test_frame is not None and test_frame.size > 0:
                print(f"✅ Camera working: {test_frame.shape}")
                print("   Green light should appear now!")
                break
            else:
                print(f"   Attempt {attempt + 1}/{max_attempts}: Frame capture failed, retrying...")
                time.sleep(0.2)
        else:
            print("❌ Camera test failed after multiple attempts")
            print("   (Camera may still work during main processing)")
    else:
        print("❌ Camera not accessible")
    print()

    # Add real-time display by overriding process_frame
    original_process_frame = hpe.process_frame
    
    def process_frame_with_display(frame, frame_number, bitrate_samples, last_bitrate_time):
        # Convert frame to numpy array for processing
        if isinstance(frame, torch.Tensor):
            frame_np = frame.cpu().numpy()
            frame_np = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
        else:
            frame_np = frame.copy()
        
        # Create display frame (copy of original)
        display_frame = frame_np.copy()
        
        # Debug: Check if frame is valid
        if display_frame is None or display_frame.size == 0:
            print(f"ERROR: Invalid frame at frame {frame_number}")
            return
        
        # Calculate frame size in bytes (needed for bitrate monitoring)
        frame_bytes = display_frame.nbytes
        
        # Debug: Print frame info (only for first few frames)
        if frame_number < 3:
            frame_mb = frame_bytes / (1024 * 1024)
            
            # Calculate theoretical bitrate (raw uncompressed data)
            fps = hpe.cap.get(cv2.CAP_PROP_FPS)
            bitrate_bps = frame_bytes * 8 * fps  # bits per second
            bitrate_mbps = bitrate_bps / (1024 * 1024)  # Mbps
            
            print(f"Frame {frame_number}: shape={display_frame.shape}, dtype={display_frame.dtype}, min={display_frame.min()}, max={display_frame.max()}")
            print(f"  Frame size: {frame_bytes:,} bytes ({frame_mb:.2f} MB)")
            print(f"  Theoretical bitrate: {bitrate_bps:,.0f} bps ({bitrate_mbps:.2f} Mbps) @ {fps:.1f} FPS")
            print(f"Frame {frame_number}: This should show your camera feed with a blue test rectangle")
        
        # Process the frame to get pose detection results
        start_time = time.time()
        
        # Preprocess frame
        padded = hpe.pad_and_resize(frame_np)
        
        
        # Run inference
        predictions = hpe.run_model(padded)
        
        # Debug: Check what the model returns
        if frame_number < 3:
            print(f"Model predictions type: {type(predictions)}")
            if isinstance(predictions, tuple):
                poses_len = len(predictions[0]) if predictions[0] is not None else 0
                scores_len = len(predictions[1]) if predictions[1] is not None else 0
                print(f"Predictions tuple: poses={poses_len}, scores={scores_len}")
                print(f"Poses shape: {predictions[0].shape if predictions[0] is not None else 'None'}")
                print(f"Scores shape: {predictions[1].shape if predictions[1] is not None else 'None'}")
            else:
                print(f"Predictions: {predictions}")
        
        # Postprocess to get bodies (using model's default filtering)
        bodies = hpe.postprocess(predictions)
        
        # Debug: Print pose detection results
        if frame_number < 5:  # Only for first 5 frames
            print(f"Frame {frame_number}: Found {len(bodies) if bodies else 0} poses")
            if bodies:
                for i, body in enumerate(bodies):
                    print(f"  Pose {i}: score={body.score:.3f}, bbox=({body.xmin},{body.ymin},{body.xmax},{body.ymax})")
                    print(f"    Keypoints: {len(body.keypoints) if hasattr(body, 'keypoints') else 'N/A'}")
                    if hasattr(body, 'keypoints') and body.keypoints is not None:
                        print(f"    Keypoint scores: {body.keypoints_score[:5] if len(body.keypoints_score) > 5 else body.keypoints_score}")
        
        # Calculate timing
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Update FPS calculation (similar to base class)
        hpe.processing_times.append(processing_time_ms)
        if len(hpe.processing_times) > hpe.max_processing_times_len:
            hpe.processing_times.popleft()
        
        # Calculate FPS
        if hpe.processing_times:
            mean_time = sum(hpe.processing_times) / len(hpe.processing_times)
            fps = 1000 / mean_time if mean_time > 0 else 0
        
        # Calculate actual bitrate (every 30 frames)
        if frame_number % 30 == 0 and frame_number > 0:
            current_time = time.time()
            time_diff = current_time - last_bitrate_time
            if time_diff > 0:
                # Calculate average bitrate over last 30 frames
                avg_frame_bytes = sum(bitrate_samples) / len(bitrate_samples) if bitrate_samples else 0
                actual_bitrate_bps = (avg_frame_bytes * 8 * 30) / time_diff
                actual_bitrate_mbps = actual_bitrate_bps / (1024 * 1024)
                print(f"  Actual bitrate (last 30 frames): {actual_bitrate_bps:,.0f} bps ({actual_bitrate_mbps:.2f} Mbps)")
                bitrate_samples = []
                last_bitrate_time = current_time
        
        # Store frame size for bitrate calculation
        bitrate_samples.append(frame_bytes)
        
        # Render poses on the frame
        if bodies and hasattr(hpe, 'LINES_BODY'):
            if frame_number < 3:  # Debug for first few frames
                print(f"Rendering {len(bodies)} poses on frame {frame_number}")
            from utils.visualizer import render
            render(display_frame, bodies, hpe.LINES_BODY, 
                  hpe.score_thresh, hpe.show_scores, hpe.show_bounding_box)
        else:
            if frame_number < 3:  # Debug for first few frames
                print(f"No poses to render on frame {frame_number}: bodies={len(bodies) if bodies else 0}, LINES_BODY={hasattr(hpe, 'LINES_BODY')}")
        
        # Add timing and FPS text to frame
        cv2.putText(display_frame, f"Processing: {processing_time_ms:.1f}ms ({fps:.1f} FPS)", 
                   (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Add pose count text
        pose_count = len(bodies) if bodies else 0
        cv2.putText(display_frame, f"Poses detected: {pose_count}", 
                   (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Add best pose score if available
        if bodies and len(bodies) > 0:
            best_score = bodies[0].score
            cv2.putText(display_frame, f"Best score: {best_score:.3f}", 
                       (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        
        # Print to console (like base class)
        print(f"Inference time: {processing_time_ms:.1f}ms ({fps:.1f} FPS)", end='\r', flush=True)
        
        # Display the frame with poses rendered
        cv2.imshow('HPE Test - Press Q to quit', display_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # 'q' or ESC key
            print("\nUser pressed 'q' to quit")
            # Set a flag to stop the main loop
            hpe.should_stop = True
            return bitrate_samples, last_bitrate_time
        
        # Return updated bitrate variables
        return bitrate_samples, last_bitrate_time
    
    # Replace the process_frame method
    hpe.process_frame = process_frame_with_display
    
    # Add a flag to track if we should stop
    hpe.should_stop = False

    try:
        # Load model first (this is normally done in main_loop)
        print("Loading model...")
        hpe.load_model()
        print("Model loaded successfully!")
        
        # Custom main loop that checks for quit condition
        print("Starting custom main loop...")
        frame_number = 0
        
        while True:
            # Check if we should stop
            if hasattr(hpe, 'should_stop') and hpe.should_stop:
                print("\nStopping due to user request...")
                break
                
            # Read frame from camera
            ret, frame = hpe.cap.read()
            if not ret:
                print("\nCamera ended")
                break
                
            # Process frame and update bitrate variables
            bitrate_samples, last_bitrate_time = hpe.process_frame(frame, frame_number, bitrate_samples, last_bitrate_time)
            frame_number += 1
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        cv2.destroyAllWindows()

if __name__ == "__main__":
    test_sync_webcam()
