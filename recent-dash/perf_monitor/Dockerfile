FROM ubuntu:20.04

# Use alternative mirrors and add retry logic
RUN sed -i 's/archive.ubuntu.com/mirrors.edge.kernel.org/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.edge.kernel.org/g' /etc/apt/sources.list && \
    apt-get update --option Acquire::Retries=5 || (sleep 2 && apt-get update) && \
    apt-get install -y \
    linux-tools-common \
    linux-tools-generic \
    bpftrace \
    bc \
    procps \
    util-linux \
    docker.io \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create the /output directory
RUN mkdir -p /output && chmod -R 777 /output

# Copy the monitoring script to the container
COPY monitor_pid_perf.sh /monitor_pid_perf.sh

# Make the script executable
RUN chmod +x /monitor_pid_perf.sh

# Set the entrypoint to run the monitoring script
ENTRYPOINT ["/bin/bash", "-c", "chmod +x /monitor_pid_perf.sh && /monitor_pid_perf.sh"]