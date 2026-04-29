"""
Windows driver factory using Selenium + Appium (Appium Python client v3).

Responsible for creating and managing a single Remote WebDriver instance
that talks to the Appium Windows Driver.
"""

from __future__ import annotations

import os
from typing import Optional

import yaml
from appium import webdriver
from appium.options.windows import WindowsOptions


class WindowsDriver:
    """
    Singleton-style factory for Windows Settings Remote WebDriver.
    """

    _driver: Optional[webdriver.Remote] = None

    @classmethod
    def _load_config(cls) -> dict:
        """
        Load YAML config for driver capabilities and server URL.
        """
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        config_path = os.path.join(base_dir, "config", "config.yaml")

        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @classmethod
    def get_driver(cls) -> webdriver.Remote:
        """
        Create (if needed) and return the singleton Appium Windows driver.
        Compatible with Appium Python client v3.
        """
        if cls._driver is not None:
            return cls._driver

        config = cls._load_config()

        # --- Global / module config ---
        wa_global = config.get("winappdriver", {}) or {}
        modules_cfg = config.get("modules", {}) or {}
        settings_cfg = modules_cfg.get("settings", {}) or {}

        wa_module = settings_cfg.get("winappdriver", {}) or {}
        app_cfg = settings_cfg.get("app", {}) or {}
        timeouts_cfg = settings_cfg.get("timeouts", {}) or {}

        # --- Server & platform ---
        server_url = (
            wa_module.get("server_url")
            or wa_global.get("server_url")
            or "http://127.0.0.1:4723"
        )

        platform_name = (
            wa_module.get("platformName")
            or wa_global.get("platformName")
            or "Windows"
        )

        device_name = (
            wa_module.get("deviceName")
            or wa_global.get("deviceName")
            or "WindowsPC"
        )

        # --- App selection ---
        app_val = (
            app_cfg.get("app")
            or app_cfg.get("app_id")
            or app_cfg.get("app_path")
        )

        if not app_val:
            raise ValueError("No app/app_id/app_path defined for settings module")

        # --- Timeouts ---
        implicit_wait = timeouts_cfg.get("implicit_wait_sec", 5)
        new_command_timeout = timeouts_cfg.get("new_command_timeout_sec", 60)

        # --- Build Appium 3.x options (W3C compliant) ---
        opts = WindowsOptions()
        opts.set_capability("platformName", platform_name)      # W3C standard
        opts.set_capability("appium:automationName", "Windows")
        opts.set_capability("appium:deviceName", device_name)
        opts.set_capability("appium:app", app_val)
        opts.set_capability("appium:newCommandTimeout", new_command_timeout)

        # --- Create driver ---
        cls._driver = webdriver.Remote(
            command_executor=server_url,
            options=opts,
        )
        cls._driver.implicitly_wait(implicit_wait)

        return cls._driver

    @classmethod
    def quit_driver(cls) -> None:
        """
        Quit the driver and clean up the singleton reference.
        """
        if cls._driver is not None:
            try:
                cls._driver.quit()
            finally:
                cls._driver = None
