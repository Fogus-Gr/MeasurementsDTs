# Contact Sheet Smoke Test

Run HPE models on one image and generate a visual contact sheet.

## Examples

```bash
.venv/Scripts/python.exe tests/contact_sheet_smoke/run_contact_sheet_smoke.py --input unit_tests/images/testImage.jpg --device CPU --allow-failures
```

```bash
.venv/Scripts/python.exe tests/contact_sheet_smoke/run_contact_sheet_smoke.py --input unit_tests/images/testImage2.jpg --methods movenet openpose hrnet ae1 ae2 ae3 --device CPU
```

Outputs are written to a timestamped folder under `out/`, for example:

```text
out/contact_sheet_smoke_20260608_181700/contact_sheet.jpg
out/contact_sheet_smoke_20260608_181700/summary.json
out/contact_sheet_smoke_20260608_181700/<method>/run.log
```

Use `--allow-failures` when you want the script to exit successfully even if a
known artifact issue prevents one model, such as AlphaPose, from running.
