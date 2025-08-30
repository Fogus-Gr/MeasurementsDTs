# Videos Directory

Place your video files here for Docker deployment.

## Supported Formats
- MP4 (recommended)
- AVI
- MKV
- MOV
- WebM

## File Naming
- Default: `video.mp4` (automatically used by Docker)
- Custom: Specify with `--video` argument or `VIDEO_FILE` environment variable

## Examples

```bash
# Default usage (expects video.mp4)
docker run -v ./videos:/app/videos:ro h264-streaming-server

# Custom video file
docker run -e VIDEO_FILE=/app/videos/my-movie.mp4 -v ./videos:/app/videos:ro h264-streaming-server
```

## Production Tips
- Use H.264 encoded videos for best performance
- Keep file sizes reasonable (< 2GB for better memory usage)
- Test videos locally before deploying
