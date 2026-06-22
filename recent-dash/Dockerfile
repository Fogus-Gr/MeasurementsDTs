FROM ubuntu:22.04
# Prevent interactive configuration prompts
ENV DEBIAN_FRONTEND=noninteractive
# Install VLC, its standard plugins, and networking tools
RUN apt-get update && apt-get install -y \
    vlc \
    vlc-plugin-base \
    iproute2 \
    curl \
    && rm -rf /var/lib/apt/lists/*
# VLC safely refuses to run as root. Create a non-root system user.
RUN useradd -m vlcuser
# Switch to the non-root user
USER vlcuser
WORKDIR /home/vlcuser
# Execute cvlc using the dummy interface (headless mode)
ENTRYPOINT ["cvlc", "-I", "dummy"]
