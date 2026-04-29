"""
Explicit wait helpers wrapping Selenium/Appium WebDriverWait.
"""

from typing import Callable, Any

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def wait_for(driver, condition, timeout: int = 15):
    """
    Generic explicit wait.
    """
    return WebDriverWait(driver, timeout).until(condition)


def wait_for_element_present(driver, locator, timeout: int = 15):
    """
    Wait until element located by (by, value) is present.
    """
    return wait_for(driver, EC.presence_of_element_located(locator), timeout)


def wait_for_element_visible(driver, locator, timeout: int = 15):
    """
    Wait until element located by (by, value) is visible.
    """
    return wait_for(driver, EC.visibility_of_element_located(locator), timeout)

