FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        bpftrace \
        gawk \
        tcpdump \
        iproute2 \
        procps \
        net-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/tracer

COPY trace_container_net.sh .

RUN chmod +x trace_container_net.sh

ENTRYPOINT ["/bin/bash"]