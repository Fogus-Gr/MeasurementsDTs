```yaml
version: '3.8'

services:
  # Your existing services here...
  # h264-streaming-server, hpe, etc.

  video-tracer:
    build:
      context: .
      dockerfile: bpftrace-tracer/Dockerfile.wind
    container_name: video-tracer
    restart: unless-stopped
    network_mode: "host"  # Required for network monitoring
    cap_add:
      - SYS_ADMIN
      - SYS_RESOURCE
      - NET_ADMIN
      - BPF  # Required for bpftrace
    security_opt:
      - seccomp=unconfined
    volumes:
      - ./bpftrace-tracer/output:/opt/tracer/output
      - /sys/kernel/debug:/sys/kernel/debug:ro
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
    environment:
      - TARGET_PORT=8089
      - NETIF=eth0
      - SAMPLE_RATE_MS=100
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 200M
    healthcheck:
      test: ["CMD", "test", "-f", "/opt/tracer/output/trace.csv"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```