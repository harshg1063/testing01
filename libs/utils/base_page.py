"""
Base Page class for Windows Settings Page Objects.

This wraps the Appium Windows driver and provides helpers to read
locators from the JSON ui_map.
"""

import json
import os
from typing import Any, Dict

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from libs.utils.waits import wait_for_element_visible


class BasePage:
    """
    Common functionality for all Windows Settings pages.

    NOTE:
    This class is designed to work with a ui_map JSON that follows
    the structure you provided, for example:

    {
      "app": { ... },
      "locators": {
        "nav": {
          "system_tab": { "locator": { "AutomationID": "SystemButton" } }
        }
      },
      "testdata": { ... }
    }
    """

    def __init__(self, driver: WebDriver, ui_map_file: str):
        self.driver = driver
        self._ui_map = self._load_ui_map(ui_map_file)
        # Work from the "locators" section by default
        self._locators = self._ui_map.get("locators", {})

    @staticmethod
    def _load_ui_map(file_name: str) -> Dict[str, Any]:
        """
        Load the complete ui_map JSON file.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base_dir, "resource", "ui_map", "windows", file_name)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _resolve_locator(self, key_path: str):
        """
        Resolve a dotted key path into a Selenium/Appium locator tuple.

        key_path is relative to the \"locators\" section, for example:
        - \"nav.system_tab\"
        - \"system_display.brightness_slider\"

        Each leaf node is expected to look like:
        { \"locator\": { \"AutomationID\": \"...\" } }
        or
        { \"locator\": { \"name\": \"...\" } }
        """
        node = self._locators
        for part in key_path.split("."):
            node = node[part]

        locator_def = node.get("locator", node)

        if "AutomationID" in locator_def:
            return By.ACCESSIBILITY_ID, locator_def["AutomationID"]
        if "name" in locator_def:
            return By.NAME, locator_def["name"]
        if "xpath" in locator_def:
            return By.XPATH, locator_def["xpath"]
        if "id" in locator_def:
            return By.ID, locator_def["id"]

        raise ValueError(f"Unsupported locator format in ui_map for key '{key_path}': {locator_def}")

    def find(self, key_path: str):
        locator = self._resolve_locator(key_path)
        return self.driver.find_element(*locator)

    def click(self, key_path: str):
        el = wait_for_element_visible(self.driver, self._resolve_locator(key_path))
        el.click()
        return el

    def get_text(self, key_path: str) -> str:
        el = wait_for_element_visible(self.driver, self._resolve_locator(key_path))
        return el.text


