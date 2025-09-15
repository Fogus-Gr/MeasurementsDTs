FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install minimal dependencies
RUN apt-get update && \
    apt-get install -y ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install docker

# Copy application files
COPY network_monitor.py /app/
COPY entrypoint.sh /app/

# Set entrypoint and permissions
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Health check to verify container is running
HEALTHCHECK --interval=5s --timeout=3s \
    CMD ps aux | grep network_monitor.py || exit 1
