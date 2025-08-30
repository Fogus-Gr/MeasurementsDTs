#!/bin/bash

VIDEO_URL="$1"

if [ -z "$VIDEO_URL" ]; then
    echo "Usage: $0 <video_url>"
    exit 1
fi

# Run ffprobe and curl checks (single ffprobe call for speed)
INFO=$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,codec_type,width,height,r_frame_rate,pix_fmt \
    -of default=noprint_wrappers=1 "$VIDEO_URL")

CODEC=$(echo "$INFO" | grep codec_name | head -n1 | cut -d= -f2)
RESOLUTION=$(echo "$INFO" | grep width | head -n1 | cut -d= -f2),$(echo "$INFO" | grep height | head -n1 | cut -d= -f2)
WIDTH=$(echo "$INFO" | grep width | head -n1 | cut -d= -f2)
HEIGHT=$(echo "$INFO" | grep height | head -n1 | cut -d= -f2)
FPS=$(echo "$INFO" | grep r_frame_rate | head -n1 | cut -d= -f2)
PIX_FMT=$(echo "$INFO" | grep pix_fmt | head -n1 | cut -d= -f2)
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$VIDEO_URL")

# Compatibility checks
CODEC_COMPAT=$( [[ "$CODEC" == "h264" ]] && echo "YES" || echo "NO" )
PIX_FMT_COMPAT=$( [[ "$PIX_FMT" == "yuv420p" ]] && echo "YES" || echo "NO" )
ACCESS_COMPAT=$( [[ "$HTTP_STATUS" == "200" ]] && echo "YES" || echo "NO" )
# Resolution: width >= 320, height >= 240, width <= 4096, height <= 2160
if [[ -n "$WIDTH" && -n "$HEIGHT" && $WIDTH =~ ^[0-9]+$ && $HEIGHT =~ ^[0-9]+$ ]]; then
    if [[ $WIDTH -ge 320 && $HEIGHT -ge 240 && $WIDTH -le 4096 && $HEIGHT -le 2160 ]]; then
        RES_COMPAT="YES"
    else
        RES_COMPAT="NO"
    fi
else
    RES_COMPAT="NO"
    echo "Warning: Could not determine width/height from ffprobe output." >&2
fi
# FPS: between 10 and 60
FPS_NUM=$(echo $FPS | awk -F'/' '{if ($2>0) print $1/$2; else print $1;}')
if (( $(echo "$FPS_NUM >= 10 && $FPS_NUM <= 60" | bc -l) )); then
    FPS_COMPAT="YES"
else
    FPS_COMPAT="NO"
fi

# Print summary table with details
printf "\n%-15s | %-30s | %-20s | %-10s\n" "Property" "Check (command)" "Result" "Compatible?"
printf '%s\n' "-------------------------------------------------------------------------------------------------------------"
printf "%-15s | %-30s | %-20s | %-10s\n" "Codec" "ffprobe stream=codec_name" "$CODEC" "$CODEC_COMPAT"
printf "%-15s | %-30s | %-20s | %-10s\n" "Resolution" "ffprobe stream=width,height" "$RESOLUTION" "$RES_COMPAT"
printf "%-15s | %-30s | %-20s | %-10s\n" "Width" "ffprobe stream=width" "$WIDTH" "-"
printf "%-15s | %-30s | %-20s | %-10s\n" "Height" "ffprobe stream=height" "$HEIGHT" "-"
printf "%-15s | %-30s | %-20s | %-10s\n" "FPS" "ffprobe stream=r_frame_rate" "$FPS" "$FPS_COMPAT"
printf "%-15s | %-30s | %-20s | %-10s\n" "Pixel Format" "ffprobe stream=pix_fmt" "$PIX_FMT" "$PIX_FMT_COMPAT"
printf "%-15s | %-30s | %-20s | %-10s\n" "Accessibility" "curl GET" "HTTP $HTTP_STATUS" "$ACCESS_COMPAT"
printf "%-15s | %-30s | %-20s | %-10s\n" "Continuity" "ffplay or VLC" "Manual check" "See below"

# Overall compatibility verdict
if [[ "$CODEC_COMPAT" == "YES" && "$PIX_FMT_COMPAT" == "YES" && "$RES_COMPAT" == "YES" && "$FPS_COMPAT" == "YES" && "$ACCESS_COMPAT" == "YES" ]]; then
    OVERALL="COMPATIBLE"
else
    OVERALL="NOT COMPATIBLE"
fi

echo
printf "Overall verdict: %s (for OpenCV/AlphaPose)\n" "$OVERALL"

# Print all details from ffprobe for reference
printf '\nDetails from ffprobe (for debugging):\n'
echo "$INFO"

echo
printf "For continuity, run: ffplay \"$VIDEO_URL\" and check for smooth playback and no errors.\n"

# Protocol check and OpenCV FFMPEG options advice
if [[ "$VIDEO_URL" =~ ^rtsp:// ]]; then
    PROTO="RTSP"
    OPENCV_HINT="For RTSP streams, you may need to set OPENCV_FFMPEG_CAPTURE_OPTIONS, e.g.:
  export OPENCV_FFMPEG_CAPTURE_OPTIONS='rtsp_transport;tcp|buffer_size;1048576'"
elif [[ "$VIDEO_URL" =~ ^http:// || "$VIDEO_URL" =~ ^https:// ]]; then
    PROTO="HTTP(S)"
    OPENCV_HINT="For HTTP streams, custom OPENCV_FFMPEG_CAPTURE_OPTIONS are usually not needed."
else
    PROTO="Unknown"
    OPENCV_HINT="Unknown protocol. Please check your stream URL."
fi

echo
printf "Protocol detected: %s\n" "$PROTO"
printf "%s\n" "$OPENCV_HINT"