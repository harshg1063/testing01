"""
Page Object Model for the Windows Settings application.

Uses:
- Selenium + Appium (Windows Driver)
- ui_map defined in resource/ui_map/windows/settings.json
"""

from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver

from libs.utils.base_page import BasePage


class SettingsPage(BasePage):
    """
    High-level actions and element accessors for the Settings app.
    """

    def __init__(self, driver: WebDriver):
        super().__init__(driver, "settings.json")

    # ------------------------------------------------------------------
    # Basic checks
    # ------------------------------------------------------------------
    def is_loaded(self) -> bool:
        """
        Check that the Settings main window is loaded by verifying
        that the System tab is present.
        """
        try:
            self.find("nav.system_tab")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------
    def go_to_system_display(self):
        """
        Navigate to System > Display page.
        """
        self.click("nav.system_tab")
        self.click("system_display.display_menu_item")

    def go_to_time_language_home(self):
        """
        Navigate to Time & language home.
        """
        self.click("nav.time_language_tab")

    def go_to_date_time(self):
        """
        Navigate to Time & language > Date & time.
        """
        self.go_to_time_language_home()
        self.click("time_language.date_time_menu_item")

    def go_to_language_region(self):
        """
        Navigate to Time & language > Language & region.
        """
        self.go_to_time_language_home()
        self.click("time_language.language_region_menu_item")

    def go_to_typing(self):
        """
        Navigate to Time & language > Typing.
        """
        self.go_to_time_language_home()
        self.click("time_language.typing_menu_item")

    def go_to_personalization_home(self):
        """
        Navigate to Personalization home page.
        """
        self.click("nav.personalization_tab")

    def go_to_personalization_background(self):
        self.go_to_personalization_home()
        self.click("personalization.background_menu_item")

    def go_to_personalization_themes(self):
        self.go_to_personalization_home()
        self.click("personalization.theme_menu_item")

    def go_to_personalization_colors(self):
        self.go_to_personalization_home()
        self.click("personalization.colors_menu_item")

    def go_to_personalization_lock_screen(self):
        self.go_to_personalization_home()
        self.click("personalization.lock_screen_menu_item")

    def go_to_personalization_start(self):
        self.go_to_personalization_home()
        self.click("personalization.start_menu_item")

    def go_to_personalization_taskbar(self):
        self.go_to_personalization_home()
        self.click("personalization.taskbar_menu_item")

    # ------------------------------------------------------------------
    # System > Display actions
    # ------------------------------------------------------------------
    def is_brightness_slider_visible(self) -> bool:
        return self.find("system_display.brightness_slider").is_displayed()

    def toggle_night_light(self):
        """
        Click the Night light toggle.
        """
        self.click("system_display.night_light_toggle")

    # ------------------------------------------------------------------
    # Time & language actions
    # ------------------------------------------------------------------
    def toggle_set_time_automatically(self):
        self.click("time_language.set_time_automatically")

    def toggle_set_timezone_automatically(self):
        self.click("time_language.set_timezone_automatically")

    def click_sync_now(self):
        self.click("time_language.sync_now_button")

    def toggle_typing_suggestions(self):
        self.click("time_language.typing_suggestions_toggle")

    def toggle_autocorrect(self):
        self.click("time_language.autocorrect_toggle")

    # ------------------------------------------------------------------
    # Personalization actions
    # ------------------------------------------------------------------
    def toggle_dark_mode(self):
        self.click("personalization.dark_mode_radio")

    def toggle_light_mode(self):
        self.click("personalization.light_mode_radio")

    def toggle_start_recent_apps(self):
        self.click("personalization.start_recent_apps_toggle")

    def toggle_taskbar_auto_hide(self):
        self.click("personalization.taskbar_auto_hide_toggle")

