
# Prerequisites

- `bc` on the host for timestamp/startup timing.

# Build info

First we build the images
```
sudo docker compose build
```

Then we start the containers
```
sudo docker compose up
```

# Stream
To connect using the VLC
1. You need the exposed host port that the HTTP Client server is listening on
2. Open VLC and select Media > Open video stream
3. Insert the URL `http://<SERVER_IP>:<EXPOSED_HTTP_CLIENT_PORT>/manifest.mpd`
4. Click play and enjoy.
