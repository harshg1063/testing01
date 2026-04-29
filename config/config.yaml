winappdriver:
  server_url: "http://127.0.0.1:4723"
  platformName: "Windows"
  deviceName: "WindowsPC"

modules:
  settings:
    app:
      app_id: "SystemSettings"  # AppId for Windows Settings
    winappdriver:
      # Optional overrides for this module (fallback to top-level winappdriver)
      server_url: "http://127.0.0.1:4723"
      deviceName: "WindowsPC"
      platformName: "Windows"
    timeouts:
      implicit_wait_sec: 5
      new_command_timeout_sec: 60
    resources:
      # Path to the UI map JSON used by SettingsPage
      ui_map: "resource/ui_map/windows/settings.json"
