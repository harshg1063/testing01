# Shared scripts

This folder holds repo-level helper scripts for running tests.

## devices.json
Each entry defines a device the test runner can target:
- `name`: friendly device name used with `-Device`
- `url`: executor host name
- `port`: executor port
- `target`: test target value (usually same as host)

## run-asqe.ps1
Wrapper script that reads `devices.json` and runs pytest without retyping host/port.

Note: If you do not pass `-Device`, the script picks one random device from `devices.json`.

You can run the command from the repo root or from the scripts folder. The only
difference is the path you pass to `-File` and `-TestPath`.

Examples (repo root):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-asqe.ps1 -TestPath tests\hp_app\video_control\test_x.py -Device Goldy
powershell -ExecutionPolicy Bypass -File .\scripts\run-asqe.ps1 -TestPath tests\hp_app\video_control\test_x.py -Device Sammy,Goldy -NewWindow
```

Example (from scripts folder):

```powershell
cd scripts
powershell -ExecutionPolicy Bypass -File .\run-asqe.ps1 -TestPath ..\tests\hp_app\video_control\test_x.py -Device Goldy
```
