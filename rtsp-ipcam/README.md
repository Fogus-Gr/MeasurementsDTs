# Direct H.264 Video Streaming Server

A simple and reliable Python-based HTTP streaming server that serves H.264 video to clients like VLC and FFplay. This solution uses direct HTTP streaming instead of complex RTSP protocols for better reliability and easier setup.

## 🎯 Why This Approach?

After testing various RTSP implementations, we discovered that:
- **RTSP is complex** - Requires precise RTP packet formatting, timing, and multi-protocol coordination
- **HTTP streaming is simple** - Single protocol, direct data flow, works with all media players
- **FFmpeg handles encoding** - Let FFmpeg do what it does best while we handle the HTTP transport


[![](https://mermaid.ink/img/pako:eNptUEtPhDAQ_itkzsBSKK8ePMhm48HHQePBxUOzHaAJtKQU3XXDf7eLRj04p_km32NmznDQAoFBa_jYeU_bWnmuql6ismRfw_Nttdntxp6fNtdGv09oanj1guDKu2-lOv6lx47-YDs03_gf4tquw5s4o49o3tA4VedAMFmDfJCqDaZ17uTgu72kANbwfkIfBjQDv2A4X_xqcGkD1sBcK7Dhc-9Ca7U43cjVi9YDMGtmpzR6brsfn3kU3OJWcnf1LwWVQFPpWVlgJMpWD2BnOALLaUhLQilNaZrRNEl9OAErSVhkJSFxkcR5SRYfPtbIKMzjhNAoTfI8KQofUEirzd3Xpw9aNbKF5RP9VXUP?type=png)](https://mermaid.live/edit#pako:eNptUEtPhDAQ_itkzsBSKK8ePMhm48HHQePBxUOzHaAJtKQU3XXDf7eLRj04p_km32NmznDQAoFBa_jYeU_bWnmuql6ismRfw_Nttdntxp6fNtdGv09oanj1guDKu2-lOv6lx47-YDs03_gf4tquw5s4o49o3tA4VedAMFmDfJCqDaZ17uTgu72kANbwfkIfBjQDv2A4X_xqcGkD1sBcK7Dhc-9Ca7U43cjVi9YDMGtmpzR6brsfn3kU3OJWcnf1LwWVQFPpWVlgJMpWD2BnOALLaUhLQilNaZrRNEl9OAErSVhkJSFxkcR5SRYfPtbIKMzjhNAoTfI8KQofUEirzd3Xpw9aNbKF5RP9VXUP)

## ✨ Features

- 🎬 **Real-time H.264 streaming** from video files
- 🌐 **HTTP-based delivery** - works with VLC, FFplay, and web browsers
- ⚡ **Low latency** - optimized for real-time playback
- 🪟 **Windows compatible** - no complex dependencies
- 🔧 **Simple setup** - just Python and FFmpeg

## 📋 Prerequisites

- **Python 3.7+**
- **FFmpeg** (must be in PATH)
- **Docker** (optional, for containerized deployment)

### Quick Validation (Windows)

Run the validation script to check if everything is set up correctly:
```powershell
.\validate.ps1
```

This will check:
- Python installation and version
- FFmpeg availability 
- Docker installation and daemon status
- Required project files
- Port availability
- Video files in the videos directory

### Windows-Specific Setup

**For PowerShell users (Recommended):**
- PowerShell 5.0+ (built into Windows 10/11)
- Use `build.ps1` script for all Docker operations

**For Make users (Optional):**
- Install Make for Windows:
  - Via Chocolatey: `choco install make`
  - Via Scoop: `scoop install make`
  - Via Git Bash (comes with Git for Windows)
  - Manual download from GnuWin32

**FFmpeg Installation on Windows:**
1. Download from https://ffmpeg.org/download.html
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your system PATH
4. Verify: `ffmpeg -version`

## 🚀 Quick Start

### 1. Start the Streaming Server

**Option A: Command Line (Cross-platform)**
```bash
# Windows
python direct_stream_server.py --video "C:\path\to\your\video.mp4"

# Linux/macOS
python direct_stream_server.py --video "/path/to/your/video.mp4"

# Custom port
python direct_stream_server.py --video "video.mp4" --port 9090
```

**Option B: Using batch/shell scripts**
```bash
# Windows - Edit start_server.bat with your video path
start_server.bat

# Linux/macOS - Make executable and run
chmod +x start_server.sh
./start_server.sh /path/to/video.mp4
```

**Option C: Using VS Code**
- Edit the launch configuration with your video path
- Press `F5` to debug, or run the "Start Direct H.264 Server" task

**Option D: Using Docker (Recommended for Production)**
```bash
# Quick start with Docker
make setup                    # Create necessary directories
cp your-video.mp4 ./videos/video.mp4  # Add your video
make build                    # Build Docker image
make run                      # Start container

# Or using docker-compose
docker-compose up -d

# With custom video file
docker run -d \
  --name h264-streaming-server \
  -p 8080:8080 \
  -v /path/to/your/videos:/app/videos:ro \
  h264-streaming-server
```

### 2. Test the Stream

**With VLC Media Player:**
1. Open VLC
2. Media → Open Network Stream
3. Enter: `http://localhost:8080/stream.h264`
4. Click Play

**With FFplay (command line):**
```bash
ffplay http://localhost:8080/stream.h264
```

## 📁 Project Structure

```
rtsp-ipcam/
├── direct_stream_server.py    # Main HTTP streaming server
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose setup
├── .dockerignore             # Docker ignore file
├── Makefile                  # Docker automation commands (cross-platform)
├── build.ps1                 # PowerShell build script (Windows alternative)
├── validate.ps1              # Windows system validation script
├── nginx.conf                # Nginx reverse proxy config
├── .env.example              # Environment variables template
├── start_server.bat          # Windows batch file
├── start_server.sh           # Linux/macOS shell script  
├── requirements.txt          # Python dependencies (minimal)
├── README.md                 # This file
└── .vscode/                  # VS Code configuration
    ├── tasks.json            # Build tasks
    └── launch.json           # Debug configuration
```

## 🐳 Docker Deployment

### Quick Start with Docker

**Linux/macOS (using Make):**
```bash
# 1. Setup directories and build
make setup
make build

# 2. Add your video file
cp your-video.mp4 ./videos/video.mp4

# 3. Run the container
make run

# 4. Test the stream
make test
```

**Windows (using PowerShell):**
```powershell
# 1. Setup directories and build
.\build.ps1 setup
.\build.ps1 build

# 2. Add your video file
Copy-Item your-video.mp4 .\videos\video.mp4

# 3. Run the container
.\build.ps1 run

# 4. Test the stream
.\build.ps1 test
```

**Windows (using Make - requires Make for Windows):**
```cmd
# Same commands as Linux/macOS above
make setup
make build
# ... etc
```

### Docker Commands

**Linux/macOS:**
```bash
# Development mode (with live logs)
make run-dev

# Production mode (with Nginx proxy)
make run-prod

# View logs
make logs

# Stop and cleanup
make stop
make clean

# Get container shell
make shell
```

**Windows PowerShell:**
```powershell
# Development mode (with live logs)
.\build.ps1 run-dev

# Production mode (with Nginx proxy)
.\build.ps1 run-prod

# View logs
.\build.ps1 logs

# Stop and cleanup
.\build.ps1 stop
.\build.ps1 clean

# Get container shell
.\build.ps1 shell

# Check status and health
.\build.ps1 status
.\build.ps1 health
```

### Manual Docker Usage

```bash
# Build image
docker build -t h264-streaming-server .

# Run with volume mount
docker run -d \
  --name h264-streaming-server \
  -p 8080:8080 \
  -v ./videos:/app/videos:ro \
  h264-streaming-server

# Custom video file and port
docker run -d \
  --name h264-streaming-server \
  -p 9090:8080 \
  -v /path/to/videos:/app/videos:ro \
  -e VIDEO_FILE=/app/videos/custom-video.mp4 \
  h264-streaming-server
```

### Production Deployment

For production, use docker-compose with Nginx reverse proxy:

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Start with production profile
docker-compose --profile production up -d
```

### Docker Features

- ✅ **Multi-stage build** - Optimized image size
- ✅ **Non-root user** - Enhanced security
- ✅ **Health checks** - Container monitoring
- ✅ **Resource limits** - CPU and memory constraints
- ✅ **Read-only filesystem** - Security hardening
- ✅ **Nginx proxy** - Production-ready reverse proxy
- ✅ **Environment variables** - Flexible configuration

## ⚙️ Command Line Options

```bash
python direct_stream_server.py --help
```

**Available options:**
- `--video, -v` (required): Path to the video file to stream
- `--port, -p` (optional): Port number for HTTP server (default: 8080)

**Examples:**
```bash
# Basic usage
python direct_stream_server.py --video "my_video.mp4"

# Windows with full path
python direct_stream_server.py --video "C:\Users\theo\Downloads\video.mp4"

# Linux/macOS with full path  
python direct_stream_server.py --video "/home/user/Documents/video.mp4"

# Custom port
python direct_stream_server.py --video "video.mp4" --port 9090

# Short options
python direct_stream_server.py -v "video.mp4" -p 8080
```

## ⚙️ How It Works

1. **HTTP Server** - Python's built-in HTTP server handles client connections
2. **FFmpeg Subprocess** - Spawns FFmpeg to encode your video file in real-time
3. **Direct Streaming** - Pipes H.264 data directly from FFmpeg to HTTP response
4. **Client Playback** - VLC/FFplay receive and decode the H.264 stream

```
Video File → FFmpeg → HTTP Server → Client (VLC/FFplay)
```

## 🔧 Configuration

The server now accepts any video file via command line arguments:

### Server Settings
- **Port**: Default 8080 (use `--port` to change)
- **Host**: 0.0.0.0 (accepts connections from any IP)
- **Endpoint**: `/stream.h264`

### Video File Support
- **Cross-platform paths**: Uses Python's `pathlib` for Windows/Linux/macOS compatibility
- **File validation**: Checks if file exists before starting server
- **Absolute paths**: Automatically resolves relative to absolute paths

### FFmpeg Settings
- **Codec**: libx264 (H.264)
- **Preset**: ultrafast (low CPU usage)
- **Tune**: zerolatency (minimal delay)
- **Format**: raw H.264 stream

## 🛠️ Customization

### Stream Different Video Files
Edit the `video_path` in `direct_stream_server.py`:
```python
video_path = r"C:\path\to\your\video.mp4"
```

### Add Multiple Streams
You can extend the server to handle multiple video endpoints:
```python
def do_GET(self):
    if self.path == '/video1.h264':
        # Stream video 1
    elif self.path == '/video2.h264':
        # Stream video 2
```

### Change Streaming Quality
Modify the FFmpeg command in the server:
```python
cmd = [
    'ffmpeg',
    '-re', '-i', video_path,
    '-c:v', 'libx264',
    '-preset', 'medium',      # higher quality
    '-crf', '20',             # quality setting
    '-f', 'h264', '-'
]
```

## 🔍 Troubleshooting

### Common Issues

**Server Won't Start:**
- **Port in use**: Change the port with `--port 8081`
- **Python not found**: Make sure Python is in your PATH
- **File permissions**: Run as administrator if needed (Windows)

**Video Won't Play:**
- **File path**: Check that the video file path is correct
- **FFmpeg not found**: Make sure FFmpeg is installed and in PATH
- **Codec issues**: Try with a different video file format

**Network Issues:**
- **Firewall**: Allow Python/HTTP traffic on port 8080
- **Localhost only**: Use your computer's IP address for remote access

### Windows-Specific Issues

**PowerShell Execution Policy:**
```powershell
# If you get execution policy errors:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Path Issues:**
```powershell
# Use forward slashes or escaped backslashes:
python direct_stream_server.py --video "C:/videos/video.mp4"
# OR
python direct_stream_server.py --video "C:\\videos\\video.mp4"
```

**Make Command Not Found:**
- Use `build.ps1` instead of `make` commands
- Or install Make via Chocolatey: `choco install make`

**Docker Desktop Issues:**
- Ensure Docker Desktop is running
- Enable WSL 2 backend if using Windows 10/11
- Check virtualization is enabled in BIOS

### Docker Issues

**Container Won't Start:**
```bash
# Check Docker logs
docker logs h264-streaming-server

# Check if port is available
netstat -an | findstr :8080  # Windows
lsof -i :8080               # Linux/macOS
```

**Volume Mount Issues:**
```bash
# Windows: Use absolute paths
docker run -v "C:\Users\YourName\videos:/app/videos:ro" ...

# Verify mount worked
docker exec -it h264-streaming-server ls -la /app/videos
```

### Testing Commands

**Check if FFmpeg is available:**
```bash
ffmpeg -version
ffplay -version
```

**Test HTTP endpoint:**
```bash
# PowerShell
Invoke-WebRequest -Uri "http://localhost:8080/stream.h264" -Method Head

# Command Prompt
curl -I http://localhost:8080/stream.h264

# Test with media player
ffplay http://localhost:8080/stream.h264
```

## 📈 Performance

- **CPU Usage**: Low with `ultrafast` preset
- **Memory**: Minimal - streams data without buffering large amounts
- **Latency**: ~1-3 seconds depending on network and client buffering
- **Concurrent Clients**: Supports multiple simultaneous viewers

## 🔄 Alternative Use Cases

This server can be adapted for:
- **Live camera streaming** - Replace file input with camera input
- **Screen capture streaming** - Use FFmpeg screen capture as input
- **Remote monitoring** - Stream to remote VLC clients
- **Web integration** - Embed in web pages using HTML5 video

## 📜 License

This project is provided as-is for educational and development purposes.

## 🎉 Success Story

This solution was developed after trying multiple RTSP implementations that had issues with:
- RTP packet timing and formatting
- NAL unit boundary detection
- Complex multi-protocol coordination
- Client-specific compatibility issues

The direct HTTP streaming approach solved all these problems with a much simpler and more reliable solution! 🚀
