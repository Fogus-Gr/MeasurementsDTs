# Simple single-stage build for H.264 streaming server
FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# Install security updates and runtime dependencies
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
    ffmpeg \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application files
COPY direct_stream_server.py .
COPY start_server.sh .

# Make shell script executable
RUN chmod +x start_server.sh

# Create videos directory for mounting
RUN mkdir -p /app/videos && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the default port
EXPOSE 8089

# Set default environment variables
ENV VIDEO_FILE="/app/videos/video.mp4"
ENV SERVER_PORT="8089"

# Default command - can be overridden
CMD python direct_stream_server.py --video "$VIDEO_FILE" --port "$SERVER_PORT"