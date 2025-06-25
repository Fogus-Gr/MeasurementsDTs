# 🧪 Flask IP Camera Simulator

This project simulates an IP camera using a Flask web server and OpenCV. It streams an `.mp4` video as an MJPEG feed over HTTP—ideal for testing vision systems, dashboards, or emulating a security camera in development environments.

---

## 📂 Project Structure

```
your_project/
├── app.py               # Flask app that streams video frames
├── Dockerfile           # Docker setup for deployment
├── videos/              # (Optional) Local directory for .mp4 files
└── docker-compose.yml   # Compose setup for easy orchestration
```

---


## 📦 Dependencies

- Python 3.11 (in Docker)
- Flask
- OpenCV (headless)

---

## 🚀 Quick Start

### 🔨 Build the Docker Image

```bash
docker build -t flask-ipcam-sim .
```

### ▶️ Run with a Custom MP4 Video (Host Volume Mount)

```bash
# Map container port 5000 to host port 8080
# Run with mounted video directory and specify which video to use
docker run \
  -v /home/user/MeasurementsDTs/videos:/app/videos:ro \
  -e VIDEO_PATH=/app/videos/ultimatum/hd_00_01.mp4 \
  -p 8080:5000 \
  flask-ipcam-sim
```

- `-v`: Mounts your host directory (with the video)
- `-e VIDEO_PATH`: Sets the video used inside the container

Then open [http://localhost:5000](http://localhost:5000) in your browser to view the simulated feed.

---

## 🧱 Docker Compose Usage

### Example `docker-compose.yml`

```yaml
version: "3.9"
services:
  ipcam:
    build: .
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - VIDEO_PATH=/app/videos/ultimatum/hd_00_01.mp4
    volumes:
      - /home/user/MeasurementsDTs/videos:/app/videos:ro
```

1. Put your `.mp4` in the `videos/` folder
2. Run:

```bash
docker-compose up --build
```

Browse to: [http://localhost:5000](http://localhost:5000)

---

## 📺 Features

- Streams `.mp4` as MJPEG via `/video_feed`
- Loops video indefinitely
- Lightweight `opencv-python-headless` build
- Hot-swappable video path using environment variable

---

## 🧪 Testing the Stream

- **Browser:** `http://localhost:5000`
- **VLC:** Open Network Stream → `http://localhost:5000/video_feed`

---

## 💬 License

MIT or yours to modify however you like—this project is meant for simulation and development purposes only.