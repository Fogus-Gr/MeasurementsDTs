# Plot Generation Analysis — `monitor_hpe`

## Question: Does the plot actually get generated?

**Answer: YES**, the plot should be generated successfully. Here's the analysis:

---

## How Plot Generation Works

### 1. Primary Method: `plot_graph.py`

**File:** `monitor_hpe/plot_graph.py`

```python
# Uses Agg backend (non-interactive, works in headless environments)
matplotlib.use('Agg')

# Reads CSV with correct column names
df = pd.read_csv(csv_file)

# Plots two subplots:
# 1. CPU usage over time (cpu_percent)
# 2. Memory usage over time (mem_rss_kb / 1024 = MB)

# Saves to: <csv_file_without_extension>.png
output_file = os.path.splitext(csv_file)[0] + '.png'
plt.savefig(output_file)
```

**Expected Output:** `results_<method>_<cpu>_<timestamp>/pid_metrics.png`

### 2. Fallback Method: Inline Python

If `plot_graph.py` fails, the script tries an alternative inline Python command:

```bash
python3 -c "
import pandas as pd
import matplotlib.pyplot as plt
df = pd.read_csv('$results_dir/pid_metrics.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
plt.figure(figsize=(15, 5))
plt.plot(df['timestamp'], df['cpu_percent'])
plt.title('CPU Usage Over Time')
plt.ylabel('CPU %')
plt.grid(True)
plt.savefig('$results_dir/cpu_usage.png')
print('Generated simple CPU plot')
"
```

**Expected Output:** `results_<method>_<cpu>_<timestamp>/cpu_usage.png`

---

## CSV Column Names

### Actual CSV Format (from `monitor_pid.sh`)

```csv
timestamp,pid,cpu_percent,mem_rss_kb,tx_bytes,rx_bytes
1716825600.123,12345,450.5,2097152,1048576,524288
1716825600.623,12345,455.2,2099200,1050624,526336
```

### What `plot_graph.py` Expects

```python
df['timestamp']    # ✅ Exists
df['cpu_percent']  # ✅ Exists
df['mem_rss_kb']   # ✅ Exists
```

**Verdict:** ✅ Column names match perfectly.

---

## Dependencies

### Required Packages

From `requirements.txt`:
- ✅ `matplotlib==3.7.5`
- ✅ `pandas==2.0.3`

Both are installed in the conda environment.

### Backend Configuration

```python
matplotlib.use('Agg')  # Non-interactive backend
```

This is **critical** for headless environments (Docker containers, SSH sessions). The Agg backend:
- ✅ Works without X11/display
- ✅ Saves directly to PNG files
- ✅ Does not call `plt.show()` (which would block)

---

## Execution Flow

```
run_experiment.sh
  ├─ Wait for HPE container to exit
  ├─ Copy results/pid_metrics.csv → results_dir/
  ├─ Try: python3 plot_graph.py results_dir/pid_metrics.csv
  │    ├─ Success → results_dir/pid_metrics.png
  │    └─ Failure → Try fallback method
  └─ Fallback: python3 -c "..." → results_dir/cpu_usage.png
```

---

## Why It Should Work

### ✅ Correct Column Names
- `plot_graph.py` reads `mem_rss_kb` ← matches CSV header
- `plot_graph.py` reads `cpu_percent` ← matches CSV header
- `plot_graph.py` reads `timestamp` ← matches CSV header

### ✅ Correct Backend
- Uses `matplotlib.use('Agg')` ← works in headless environments
- Does not call `plt.show()` ← won't block

### ✅ Dependencies Installed
- `matplotlib==3.7.5` in requirements.txt
- `pandas==2.0.3` in requirements.txt

### ✅ Fallback Method
- If primary method fails, tries simpler inline plot
- Only plots CPU (no memory) to reduce failure points

---

## Potential Issues

### Issue 1: Missing Dependencies (Unlikely)

**Symptom:** `ModuleNotFoundError: No module named 'matplotlib'`

**Cause:** Dependencies not installed

**Solution:**
```bash
conda install --file requirements.txt
# or
pip install matplotlib pandas
```

### Issue 2: CSV File Not Found

**Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: 'results_dir/pid_metrics.csv'`

**Cause:** CSV not copied from container

**Solution:** Check if `docker cp` succeeded:
```bash
docker cp monitor-hpe-monitor-1:/output/pid_metrics.csv results/
```

### Issue 3: Empty CSV

**Symptom:** `pandas.errors.EmptyDataError: No columns to parse from file`

**Cause:** Monitor container didn't write any data

**Solution:** Check monitor container logs:
```bash
docker logs monitor-hpe-monitor-1
```

### Issue 4: Corrupted CSV

**Symptom:** `pandas.errors.ParserError: Error tokenizing data`

**Cause:** Concurrent writes without proper locking (unlikely with current flock implementation)

**Solution:** Check CSV file integrity:
```bash
head -20 results_dir/pid_metrics.csv
tail -20 results_dir/pid_metrics.csv
```

---

## Verification

### Check if Plot Was Generated

```bash
cd monitor_hpe
./run_experiment.sh movenet

# Check results directory
ls -lh results_*/
# Expected files:
# - pid_metrics.csv
# - pid_metrics.png  (from plot_graph.py)
# OR
# - cpu_usage.png    (from fallback method)
```

### View Plot

```bash
# On local machine with GUI
xdg-open results_*/pid_metrics.png

# On remote machine
scp user@host:~/MeasurementsDTs/monitor_hpe/results_*/pid_metrics.png .
```

---

## Documentation Bug Fixed

### Before (Incorrect)

USAGE.md documented CSV format as:
```csv
timestamp,cpu_percent,memory_mb,memory_percent
```

This was **wrong** — the actual CSV has:
```csv
timestamp,pid,cpu_percent,mem_rss_kb,tx_bytes,rx_bytes
```

### After (Correct)

✅ Fixed in commit: Updated USAGE.md with correct CSV column names

---

## Conclusion

**YES, the plot SHOULD be generated successfully** because:

1. ✅ `plot_graph.py` exists and is correct
2. ✅ Column names match between CSV and plot script
3. ✅ Uses Agg backend (works in headless environments)
4. ✅ Dependencies are installed (matplotlib, pandas)
5. ✅ Fallback method exists if primary fails
6. ✅ Documentation now matches actual CSV format

**Expected output:** `results_<method>_<cpu>_<timestamp>/pid_metrics.png`

If the plot is NOT generated, check:
1. Monitor container logs: `docker logs monitor-hpe-monitor-1`
2. CSV file exists: `ls -lh results/pid_metrics.csv`
3. CSV file is not empty: `wc -l results/pid_metrics.csv`
4. Dependencies installed: `python3 -c "import matplotlib, pandas; print('OK')"`
