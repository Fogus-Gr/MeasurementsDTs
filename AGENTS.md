# Repository Guidelines

## Project Structure & Module Organization
- Core entrypoint: `main.py` (selects HPE method via `--method`).
- Models and backends: `models/AlphaPose`, `models/MoveNet`, `models/OpenVINO`.
- Implementations: `alphapose_hpe.py`, `movenet_hpe.py`, `openvino_base_hpe.py`, with helpers in `utils/`.
- Dev utilities: `dev_tools/` (e.g., `stream_video_server.py`).
- Tests and sample assets: `unit_tests/` (images, video), `test/` (large sample video).
- Packaging/build: `setup.py` (Cython/CUDA extensions for AlphaPose), `requirements.txt`.

## Build, Test, and Development Commands
- Create env and install deps:
  - `conda create -n hpe python=3.8.10 -y && conda activate hpe`
  - `conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch`
  - `conda install --file requirements.txt`
- Build AlphaPose extensions (CPU/GPU as available):
  - `bash models/AlphaPose/build_extensions.sh` or `python setup.py build_ext --inplace`
- Run locally (examples):
  - `python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image`
  - `python3 main.py --method alphapose --input unit_tests/images/ --json`
- Dev streaming helper:
  - `python3 dev_tools/stream_video_server.py` then point `--input http://<ip>:8080/video_feed`.

## Coding Style & Naming Conventions
- Python 3.8; use 4-space indents, Black-like formatting, and type hints where feasible.
- Filenames: snake_case for modules; Classes in CapWords; functions/vars in snake_case.
- Prefer explicit imports; avoid wildcard imports.
- Keep CLI flags consistent with existing patterns (`--long-option`, hyphenated names).

## Testing Guidelines
- Use lightweight, deterministic samples in `unit_tests/` for functional checks.
- Add tests alongside modules or under `unit_tests/` mirroring paths (e.g., `unit_tests/test_movenet_hpe.py`).
- Run smoke tests by executing `main.py` with small inputs; prefer CPU for CI.
- If introducing new parsers/IO, include I/O round-trip tests and guard large assets behind flags.

## Commit & Pull Request Guidelines
- Commits: concise imperative summary (<=72 chars), body explaining rationale and perf/accuracy impact.
- Reference issues with `Fixes #123` or `Refs #123` when applicable.
- PRs must include: description, reproduction steps, command examples, screenshots or short clips (when visual changes), and notes on model files needed.
- For performance-related PRs, include before/after metrics and commands used.

## Security & Configuration Tips
- Do not commit large binaries or private model files; use the paths documented in `README.md`.
- Validate inputs and file paths; avoid executing untrusted URLs.
- GPU metrics stack via `docker-compose.yml` is optional; keep creds/secrets out of configs.
