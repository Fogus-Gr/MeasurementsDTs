# Project Architecture Diagram

This diagram shows the two main halves of the repository:

1. The HPE inference library (`main.py` + backend implementations)
2. The benchmarking rigs (`monitor_hpe/` and `ffmpeg_hpe/`)

```mermaid
flowchart LR
    %% Left side: develop/build
    subgraph Develop["Develop"]
        direction TB
        main["main.py<br/>CLI entry point"]
        base["BaseHPE<br/>shared input, padding, loop, output"]
        ap["alphapose_hpe.py<br/>YOLO + pose estimator"]
        mv["movenet_hpe.py<br/>OpenVINO MoveNet"]
        ov["openvino_base_hpe.py<br/>OpenPose, HRNet, AE1/AE2/AE3"]
        eval["utils/evaluator.py<br/>COCO JSON/CSV + bandwidth"]
        vis["utils/visualizer.py<br/>skeleton rendering"]

        main --> base
        base --> ap
        base --> mv
        base --> ov
        base --> eval
        base --> vis
    end

    subgraph Build["Build / Setup"]
        direction TB
        docker["Dockerfile_base<br/>PyTorch + OpenVINO + PyNvCodec"]
        models["Model weights + AlphaPose extensions<br/>downloaded or built during setup"]
    end

    subgraph Run["Run on Linux Node"]
        direction TB
        results["Timestamped results<br/>results-method-cpu-timestamp/"]

        subgraph RigA["monitor_hpe/<br/>baseline rig"]
            direction TB
            filein["Local image / video input"]
            monhpe["hpe container<br/>runs main.py"]
            mon["monitor_pid.sh<br/>CPU + RSS sampling"]
            fileout["out/ and CSV/JSON output"]

            filein --> monhpe --> fileout
            monhpe --> mon
        end

        subgraph RigB["ffmpeg_hpe/<br/>streaming rig"]
            direction TB
            broker["rtsp-broker<br/>MediaMTX"]
            streamer["streamer<br/>FFmpeg / NVENC"]
            hpe["hpe container<br/>main.py against RTSP stream"]
            perf["perf_monitor<br/>CPU / memory / network"]
            gpu["gpu-metrics<br/>nvidia-smi polling"]
            bcc["bcc-tracer<br/>RX byte tracing"]

            streamer --> broker --> hpe --> results
            hpe --> perf
            hpe --> gpu
            hpe --> bcc
        end
    end

    docker --> models
    docker --> main
    models --> main
    eval --> results
    vis --> results
```

## Reading the diagram

- `main.py` chooses the backend and feeds frames through `BaseHPE`.
- The backend classes implement model loading, inference, and postprocessing.
- `monitor_hpe/` is the simple local-file benchmark path.
- `ffmpeg_hpe/` is the full streaming benchmark path with RTSP, CPU/GPU monitoring, and optional BCC tracing.
- Results are written into timestamped folders so runs never overwrite each other.
