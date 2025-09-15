# Example FFmpeg streamer
FROM alpine:latest
RUN apk add --no-cache ffmpeg
COPY test.mp4 /app/
WORKDIR /app
CMD ["ffmpeg", "-re", "-stream_loop", "-1", "-i", "test.mp4", "-f", "mpegts", "http://$HPE_HOST:$HPE_PORT/process"]
