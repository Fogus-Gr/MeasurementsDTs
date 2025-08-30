"""monitors.py
Reusable monitoring classes for GPU (NVML) and CPU (psutil) with
thread‑based sampling + CSV export support. Designed to be imported
into AlphaPose benchmarking scripts or any other Python project.

Usage example:

>>> from monitors import GpuStatsMonitor, CpuStatsMonitor
>>> gpu_mon = GpuStatsMonitor(interval=0.5)
>>> cpu_mon = CpuStatsMonitor(interval=0.5)
>>> gpu_mon.start(); cpu_mon.start()
>>> ...  # run your workload here
>>> gpu_mon.stop(); cpu_mon.stop()
>>> gpu_mon.export_csv('gpu_stats.csv')
>>> cpu_mon.export_csv('cpu_stats.csv')
"""
from __future__ import annotations

import csv
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

__all__ = [
    "BaseMonitor",
    "GpuStatsMonitor",
    "CpuStatsMonitor",
]


class BaseMonitor:
    """Base class for threaded samplers.

    Attributes
    ----------
    interval : float
        Sampling interval in seconds.
    """

    def __init__(self, interval: float = 0.5):
        self.interval: float = interval
        self._records: List[Dict[str, float]] = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin sampling in a background thread."""
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        """Signal the thread to stop and wait for it to finish."""
        self._stop_event.set()
        self._thread.join()

    def export_csv(self, filepath: str) -> None:
        """Write collected records to *filepath* in CSV format."""
        if not self._records:
            raise RuntimeError("No records collected; did you forget to start()?")

        fieldnames = list(self._records[0].keys())
        with open(filepath, "w", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self._records)

    @property
    def records(self) -> List[Dict[str, float]]:
        """Return the raw in‑memory record list (read‑only)."""
        return self._records

    # ------------------------------------------------------------------
    # Context‑manager helpers
    # ------------------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()

    # ------------------------------------------------------------------
    # Internal helpers – to be overridden
    # ------------------------------------------------------------------

    def _sample(self) -> Dict[str, float]:
        """Return a single metrics dict. Subclasses must implement."""
        raise NotImplementedError

    def _run(self) -> None:
        """Thread target that periodically appends samples."""
        while not self._stop_event.is_set():
            try:
                sample = self._sample()
                if sample is not None:
                    self._records.append(sample)
            except Exception:
                # Swallow all to keep thread alive; log/debug as needed
                pass
            time.sleep(self.interval)


class GpuStatsMonitor(BaseMonitor):
    """GPU utilisation + memory monitor using NVML (nvidia-ml-py3).

    Parameters
    ----------
    gpu_index : int, default 0
        Which physical GPU to attach to.
    interval : float, default 0.5
        Sampling interval in seconds.
    """

    def __init__(self, gpu_index: int = 0, interval: float = 0.5):
        super().__init__(interval)
        try:
            import pynvml  # type: ignore
        except ModuleNotFoundError as e:
            raise ImportError("pynvml (nvidia-ml-py3) is required for GpuStatsMonitor") from e

        pynvml.nvmlInit()
        self._pynvml = pynvml
        self._handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def stop(self) -> None:  # type: ignore[override]
        super().stop()
        self._pynvml.nvmlShutdown()

    def _sample(self) -> Dict[str, float]:  # noqa: D401
        util = self._pynvml.nvmlDeviceGetUtilizationRates(self._handle)
        mem = self._pynvml.nvmlDeviceGetMemoryInfo(self._handle)

        return {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "gpu_util_percent": util.gpu,
            "gpu_mem_used_MB": round(mem.used / 1_048_576, 2),
            "gpu_mem_total_MB": round(mem.total / 1_048_576, 2),
        }


class CpuStatsMonitor(BaseMonitor):
    """CPU utilisation + RAM usage monitor using psutil."""

    def __init__(self, interval: float = 0.5):
        super().__init__(interval)
        try:
            import psutil  # type: ignore
        except ModuleNotFoundError as e:
            raise ImportError("psutil is required for CpuStatsMonitor") from e
        self._psutil = psutil

    def _sample(self) -> Dict[str, float]:
        vm = self._psutil.virtual_memory()
        return {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "cpu_percent": self._psutil.cpu_percent(interval=None),
            "ram_used_MB": round((vm.total - vm.available) / 1_048_576, 2),
            "ram_total_MB": round(vm.total / 1_048_576, 2),
        }

