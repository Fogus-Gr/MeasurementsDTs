FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install required packages including kernel headers
RUN apt-get update && \
    apt-get install -y \
        bpftrace \
        gawk \
        tcpdump \
        iproute2 \
        procps \
        net-tools \
        build-essential \
        linux-headers-generic && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/*

WORKDIR /opt/tracer

COPY trace_video_traffic.sh .

RUN chmod +x trace_video_traffic.sh

# Set the command to run the video traffic tracer
CMD ["./trace_video_traffic.sh"]