# Coordinate Smoke Test

This smoke test checks that pose keypoints stay within the input image bounds and that projected boxes do not explode in size.

## Run

```bash
python -m unittest unit_tests.test_hpe_coordinate_smoke
```

## Environment Variables

- `HPE_SMOKE_METHODS`: comma-separated list of backends to run, for example `alphapose,movenet`
- `HPE_SMOKE_TIMEOUT`: per-backend timeout in seconds, default `180`

## Examples

Run only two backends:

```bash
HPE_SMOKE_METHODS=alphapose,movenet python -m unittest unit_tests.test_hpe_coordinate_smoke
```

Increase the timeout:

```bash
HPE_SMOKE_TIMEOUT=300 python -m unittest unit_tests.test_hpe_coordinate_smoke
```

## Output

The test writes temporary results under `out/coordinate_smoke/<method>/` and expects:

- `COCOformat.json`
- `frame_0000.jpg`
