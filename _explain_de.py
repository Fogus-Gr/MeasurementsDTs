#!/usr/bin/env python3
"""Show issues D and E in context."""
import os

# --- Issue D: openvino_base_hpe.py run_model() ---
path = "openvino_base_hpe.py"
lines = open(path, encoding='utf-8').readlines()
print("=== openvino_base_hpe.py run_model() ===")
for i, line in enumerate(lines, 1):
    s = line.strip()
    if any(k in s for k in ('def run_model', 'raw_result', 'results', 'DEBUG')):
        print(f"  {i}: {s[:110]}")

print()

# --- Issue E: evaluator.py reset_results ---
path2 = "utils/evaluator.py"
lines2 = open(path2, encoding='utf-8').readlines()
print("=== utils/evaluator.py ===")
for i, line in enumerate(lines2, 1):
    s = line.strip()
    if any(k in s for k in ('def reset', 'def append', 'def save', 'global ', 'RESULTS', '_results')):
        print(f"  {i}: {s[:110]}")

print()

# Search for reset_results calls
print("=== reset_results() called from ===")
found = False
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in {'.git','__pycache__','.qoder','unit_tests','Measure_gpu_dcgm','Measure_plot_cpu_perf','Measure_Flops','.claude'}]
    for fn in files:
        if not fn.endswith('.py'):
            continue
        full = os.path.join(root, fn)
        try:
            content = open(full, encoding='utf-8', errors='ignore').read()
        except:
            continue
        for li, l in enumerate(content.splitlines(), 1):
            if 'reset_results' in l:
                print(f"  {full}:{li}: {l.strip()[:110]}")
                found = True
if not found:
    print("  (never called anywhere)")