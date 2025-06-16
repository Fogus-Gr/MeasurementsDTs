"""
Development-only script for simulating an IP video stream using Flask.
Used for local testing of IP-stream-based HPE input.

Do NOT deploy in production.
"""

from flask import Flask, Response
import cv2

app = Flask(__name__)
video_path = "unit_tests/video/giphy.gif"  # Replace with your video path
cap = cv2.VideoCapture(video_path)

def generate_frames():
    first_time = True
    while True:
        success, frame = cap.read()
        if not success:
            print("[INFO] Video ended. Replaying from start...")
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video
            continue

        if first_time:
            print("[INFO] Starting video stream...")
            first_time = False

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
