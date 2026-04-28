# Start in a new admin PowerShell window that persists after agent job ends
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Appium --address 0.0.0.0 --port 11000 --allow-cors" -Verb RunAs -WorkingDirectory "C:/Users/exec"
