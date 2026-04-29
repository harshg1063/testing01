"""
Application session management for Windows Settings.

Provides simple helpers to start and stop the Windows Settings session
around test runs.
"""

from __future__ import annotations

from libs.drivers.windows_driver import WindowsDriver


class AppSession:
    """
    High-level facade for starting/stopping the Settings application session.
    """

    @staticmethod
    def start():
        """
        Ensure the Windows Settings driver/session is up.
        """
        return WindowsDriver.get_driver()

    @staticmethod
    def stop():
        """
        Tear down the Windows Settings driver/session.
        """
        WindowsDriver.quit_driver()

