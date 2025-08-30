FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip linux-tools-common linux-tools-generic iproute2 sudo && \
    pip3 install pandas matplotlib numpy

# Add user for running perf (optional, for non-root)
RUN useradd -ms /bin/bash perfuser && echo "perfuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

WORKDIR /app

# Copy your scripts
COPY plot_perf_metrics.py /app/
COPY run_perf_plot.sh /app/

# Entrypoint
ENTRYPOINT ["bash", "/app/run_perf_plot.sh"]