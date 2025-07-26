# Suggested image name: recent_dash_proposed_caching:http_proxy
# The container will expose the service to the port 8881
# The HTTP_SERVER_DOMAIN or the HTTP_SERVER_IP environment variable should be set
# The HTTP_SERVER_PORT should be set


# This build image is used to:
#  - download the recent-dash-proposed-caching project (/opt/recent-dash-proposed-caching/)
FROM ubuntu:latest AS dash_caching_files

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
#  - Launch the HTTP Proxy (proxy server with cache)
FROM ubuntu:latest

# Default parameters
ENV HTTP_SERVER_DOMAIN=""
ENV HTTP_SERVER_IP 127.0.0.1
ENV HTTP_SERVER_PORT 8004
ENV SERVICE_IP=0.0.0.0
ENV SERVICE_PORT=80
ENV SERVICE_CACHE_FOLDER="./cache"
ENV SERVICE_ADDITIONAL_PARAMETERS="-al swg -r1 15.0 -r2 5.0 -l 250 -dl fixed -c random -s 1 -n 131"

# Prepare folders
RUN mkdir -p /opt/http_proxy/cache
WORKDIR /opt/http_proxy

# Copy files from the build image
COPY --from=dash_caching_files /opt/recent-dash-proposed-caching/cache/proxy /opt/http_proxy/proxy

# Setup launching script
COPY HTTP-Proxy.launch.sh /opt/http_proxy/launch.sh
RUN chmod +x /opt/http_proxy/launch.sh

EXPOSE 80
CMD ["/opt/http_proxy/launch.sh"]