"""
Pytest configuration for QAMA Windows Settings automation.
"""

import os
import sys

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from libs.drivers.app_session import AppSession
from libs.utils import logger as logger_module
from libs.flows.windows.settings_page import SettingsPage


@pytest.fixture(scope="session")
def logger():
    """
    Session-scoped logger fixture.
    """
    return logger_module.get_logger()


@pytest.fixture(scope="session")
def driver(logger):
    """
    Session-scoped fixture that starts the Windows Settings session.
    """
    logger.info("=" * 80)
    logger.info("Starting Windows Settings test session")
    logger.info("=" * 80)

    driver_instance = AppSession.start()
    yield driver_instance

    logger.info("=" * 80)
    logger.info("Ending Windows Settings test session")
    logger.info("=" * 80)
    AppSession.stop()


@pytest.fixture(scope="function")
def settings_page(driver):
    """
    Function-scoped SettingsPage fixture for individual tests.
    """
    return SettingsPage(driver)


def pytest_configure(config):
    """
    Register custom markers and ensure output folders exist.
    """
    # Markers
    config.addinivalue_line("markers", "smoke: smoke level tests")
    config.addinivalue_line("markers", "regression: regression suite")
    config.addinivalue_line("markers", "settings_navigation: navigation within Settings app")
    config.addinivalue_line("markers", "settings_functional: functional toggles and validations")
    config.addinivalue_line("markers", "system_display: tests for System > Display feature")
    config.addinivalue_line("markers", "time_language: tests for Time & language feature")
    config.addinivalue_line("markers", "personalization: tests for Personalization feature")

    # Ensure reports directory exists (for pytest-html output)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)


def pytest_html_report_title(report):
    """
    Customize HTML report title.
    """
    report.title = "QAMA - Windows Settings Automation Report"
