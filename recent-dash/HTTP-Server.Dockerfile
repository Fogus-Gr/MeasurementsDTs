# Suggested image name: recent_dash_proposed_caching:http_server
# Example command to create container: sudo docker run -d --name dash_http_server -p 8880:80 recent_dash_proposed_caching:http_server

# This build image is used to:
#  - download the recent-dash-proposed-caching project (/opt/recent-dash-proposed-caching/)
#  - download the video segments from a remote server (/opt/segments/)
FROM --platform=linux/amd64 ubuntu:latest AS dash_caching_files

# Install dependancies
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -qq update \
    && apt-get -qq install -y unzip wget git p7zip-full \
    && apt-get -qq autoremove \
    && apt-get -qq clean \
    && mkdir -p /opt/ \
    && cd /opt/ \
    && git clone https://github.com/Fogus-Gr/recent-dash-proposed-caching.git \
    && chmod +x /opt/recent-dash-proposed-caching/public/main \
    && chmod +x /opt/recent-dash-proposed-caching/cache/proxy \
    && chmod +x /opt/recent-dash-proposed-caching/local/local

# Commands to get segments from remote <dot>zip
#RUN mkdir -p /opt/segments \
# && wget http://ctflib.ds.unipi.gr:9001/!4CLkLLPGji/dash_segments_bbb_retranscoded_unipi.zip -O /opt/segments.zip -q \
# && unzip -q /opt/segments.zip -d /opt/segments/ \
# && rm -rf /opt/segments.zip

# Commands to get segments from remote <dot>7z
RUN mkdir -p /opt/segments
#  && wget https://gain.di.uoa.gr/DASH/dash_segments_bbb.7z -O /opt/segments.7z --no-check-certificate -q \
#  && 7z e /opt/segments.7z -o/opt/segments/ \
#  && rm -rf /opt/segments.7z
ADD segments/ /opt/segments/
RUN test -f /opt/segments/manifest.mpd || \
    (echo "Missing DASH assets. Restore recent-dash/segments/manifest.mpd before building." >&2; exit 1)

# This image is used to:
#  - Launch the HTTP server (CDN server hosting the video segments)
FROM --platform=linux/amd64 ubuntu:latest

# Default parameters
ENV SERVICE_IP=0.0.0.0
ENV SERVICE_PORT=80
ENV SERVICE_PUBLIC_FOLDER="./public"
ENV SERVICE_ADDITIONAL_PARAMETERS="-r2 5.0"

# Prepare folders
RUN mkdir -p /opt/http_server/public
WORKDIR /opt/http_server

# Copy files from the build image
COPY --from=dash_caching_files /opt/segments /opt/http_server/public
COPY --from=dash_caching_files /opt/recent-dash-proposed-caching/public/main /opt/http_server/main

# Setup launching script
COPY HTTP-Server.launch.sh /opt/http_server/launch.sh
RUN chmod +x /opt/http_server/launch.sh

EXPOSE 80
CMD ["/opt/http_server/launch.sh"]
