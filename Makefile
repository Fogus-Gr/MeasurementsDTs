SHELL := /bin/bash
PROJECT_DIR := /home/user/MeasurementsDTs

# ─────────────────────────────────────────────
#  ffmpeg_hpe — Run Experiments
# ─────────────────────────────────────────────

ffmpeg-movenet:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo ./run_experiment.sh movenet

ffmpeg-alphapose:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo ./run_experiment.sh alphapose

ffmpeg-openpose:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo ./run_experiment.sh openpose

ffmpeg-hrnet:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo ./run_experiment.sh hrnet

ffmpeg-ae1:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo ./run_experiment.sh ae1

ffmpeg-ae2:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo ./run_experiment.sh ae2

ffmpeg-ae3:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo ./run_experiment.sh ae3

# ─────────────────────────────────────────────
#  ffmpeg_hpe — Docker Builds
# ─────────────────────────────────────────────

ffmpeg-build:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo docker compose build

ffmpeg-build-hpe:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo docker compose build hpe

ffmpeg-build-perf:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo docker compose build perf_monitor

ffmpeg-build-bcc:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo docker compose build bcc-tracer

ffmpeg-build-gpu:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo docker compose build gpu-metrics

# ─────────────────────────────────────────────
#  monitor_hpe — Run Experiments
# ─────────────────────────────────────────────

monitor-movenet:
	cd $(PROJECT_DIR)/monitor_hpe && sudo ./run_experiment.sh movenet

monitor-alphapose:
	cd $(PROJECT_DIR)/monitor_hpe && sudo ./run_experiment.sh alphapose

monitor-openpose:
	cd $(PROJECT_DIR)/monitor_hpe && sudo ./run_experiment.sh openpose

monitor-hrnet:
	cd $(PROJECT_DIR)/monitor_hpe && sudo ./run_experiment.sh hrnet

monitor-ae1:
	cd $(PROJECT_DIR)/monitor_hpe && sudo ./run_experiment.sh ae1

monitor-ae2:
	cd $(PROJECT_DIR)/monitor_hpe && sudo ./run_experiment.sh ae2

monitor-ae3:
	cd $(PROJECT_DIR)/monitor_hpe && sudo ./run_experiment.sh ae3

# ─────────────────────────────────────────────
#  monitor_hpe — Docker Builds
# ─────────────────────────────────────────────

monitor-build:
	cd $(PROJECT_DIR)/monitor_hpe && sudo docker compose build

monitor-build-hpe:
	cd $(PROJECT_DIR)/monitor_hpe && sudo docker compose build hpe

monitor-build-monitor:
	cd $(PROJECT_DIR)/monitor_hpe && sudo docker compose build monitor

# ─────────────────────────────────────────────
#  Convenience
# ─────────────────────────────────────────────

build-all:
	cd $(PROJECT_DIR)/ffmpeg_hpe && sudo docker compose build
	cd $(PROJECT_DIR)/monitor_hpe && sudo docker compose build

help:
	@echo ""
	@echo "ffmpeg_hpe — experiments:"
	@echo "  make ffmpeg-movenet    make ffmpeg-alphapose  make ffmpeg-openpose"
	@echo "  make ffmpeg-hrnet      make ffmpeg-ae1        make ffmpeg-ae2        make ffmpeg-ae3"
	@echo ""
	@echo "ffmpeg_hpe — builds:"
	@echo "  make ffmpeg-build      make ffmpeg-build-hpe  make ffmpeg-build-perf"
	@echo "  make ffmpeg-build-bcc  make ffmpeg-build-gpu"
	@echo ""
	@echo "monitor_hpe — experiments:"
	@echo "  make monitor-movenet   make monitor-alphapose make monitor-openpose"
	@echo "  make monitor-hrnet     make monitor-ae1       make monitor-ae2       make monitor-ae3"
	@echo ""
	@echo "monitor_hpe — builds:"
	@echo "  make monitor-build     make monitor-build-hpe make monitor-build-monitor"
	@echo ""
	@echo "  make build-all         Build all services in both rigs"
	@echo ""

.PHONY: ffmpeg-movenet ffmpeg-alphapose ffmpeg-openpose ffmpeg-hrnet \
        ffmpeg-ae1 ffmpeg-ae2 ffmpeg-ae3 \
        ffmpeg-build ffmpeg-build-hpe ffmpeg-build-perf ffmpeg-build-bcc ffmpeg-build-gpu \
        monitor-movenet monitor-alphapose monitor-openpose monitor-hrnet \
        monitor-ae1 monitor-ae2 monitor-ae3 \
        monitor-build monitor-build-hpe monitor-build-monitor \
        build-all help
