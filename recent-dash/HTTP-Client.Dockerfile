# Suggested image name: recent_dash_proposed_caching:http_client
# Example command to create container: sudo docker run -d --name dash_http_client -p 8882:80 --env HTTP_PROXY_DOMAIN=dash_http_proxy --env HTTP_PROXY_PORT=8881 recent_dash_proposed_caching:http_local
# The container will expose the service to the port 8882
# The HTTP_PROXY_DOMAIN or the HTTP_PROXY_IP environment variable should be set
# The HTTP_PROXY_PORT should be set
# Stream to connect with VLC:  http://<HTTP_CLIENT_IP>:<HTTP_CLIENT_PORT>/manifest.mpd




# This build image is used to:
#  - download the recent-dash-proposed-caching project (/opt/recent-dash-proposed-caching/)
FROM --platform=linux/amd64 ubuntu:latest AS dash_caching_files

# Install dependancies
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -qq update \
    && apt-get -qq install -y git \
    && apt-get -qq autoremove \
    && apt-get -qq clean \
    && mkdir -p /opt/ \
    && cd /opt/ \
    && git clone https://github.com/Fogus-Gr/recent-dash-proposed-caching.git \
    && chmod +x /opt/recent-dash-proposed-caching/public/main \
    && chmod +x /opt/recent-dash-proposed-caching/cache/proxy \
    && chmod +x /opt/recent-dash-proposed-caching/local/local


# This image is used to:
#  - Launch the HTTP Client
FROM --platform=linux/amd64 ubuntu:latest

# Default parameters
ENV HTTP_PROXY_DOMAIN=""
ENV HTTP_PROXY_IP 127.0.0.1
ENV HTTP_PROXY_PORT 8004
ENV SERVICE_IP=0.0.0.0
ENV SERVICE_PORT=80
ENV SERVICE_PUBLIC_FOLDER="./public"

# Prepare folders
RUN mkdir -p /opt/http_local/public
WORKDIR /opt/http_local

# Copy files from the build image
COPY segments/manifest.mpd /opt/http_local/public/manifest.mpd
COPY --from=dash_caching_files /opt/recent-dash-proposed-caching/local/local /opt/http_local/local

# Setup launching script
COPY HTTP-Client.launch.sh /opt/http_local/launch.sh
RUN chmod +x /opt/http_local/launch.sh

EXPOSE 80
CMD ["/opt/http_local/launch.sh"]
#CMD /opt/http_local/local -a 0.0.0.0 -p 80 -sa $HTTP_PROXY_IP -sp $HTTP_PROXY_PORT -d ./public
