FROM ubuntu:20.04

# Use alternative mirrors for speed and add retry logic for resilience
RUN sed -i 's/archive.ubuntu.com/mirrors.edge.kernel.org/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.edge.kernel.org/g' /etc/apt/sources.list && \
    apt-get update --option Acquire::Retries=5 && \
    # Install only the necessary tools for performance monitoring
    apt-get install -y --no-install-recommends \
    linux-tools-common \
    linux-tools-generic \
    bpftrace \
    bc \
    procps \
    util-linux \
    sysstat \
    # Clean up apt cache to reduce image size
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a world-writable output directory to avoid UID/GID permission issues with mounted volumes
RUN mkdir -p /output && chmod 777 /output

# Copy the monitoring script to the container and set execute permissions in one step
# This is a slightly more modern syntax that reduces one image layer.
COPY --chmod=755 monitor_pid_perf.sh /monitor_pid_perf.sh

# Set the entrypoint to directly run the monitoring script.
# The script's shebang (#!/bin/bash) will ensure it's executed with bash.
ENTRYPOINT ["/monitor_pid_perf.sh"]