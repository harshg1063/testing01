"""
Tests for Windows Settings - System > Display.
"""

import pytest

from libs.utils.assertions import assert_true


@pytest.mark.settings_navigation
@pytest.mark.system_display
class TestSettingsSystemDisplay:
    """
    Around 10 tests focused on the System > Display feature set.
    """

    @pytest.mark.smoke
    def test_settings_app_launches(self, settings_page, logger):
        """
        Verify that the Settings app launches and main navigation is visible.
        """
        logger.info("Verifying Settings app launch")
        assert_true(settings_page.is_loaded(), "Settings app did not load correctly")

    @pytest.mark.smoke
    def test_navigate_to_system_display_page(self, settings_page, logger):
        """
        Navigate to System > Display and verify the header exists.
        """
        logger.info("Navigating to System > Display")
        settings_page.go_to_system_display()
        header_text = settings_page.get_text("system_display.header")
        assert_true("Display" in header_text, "Display header not visible")

    def test_brightness_slider_visible(self, settings_page, logger):
        """
        Verify that brightness slider control is visible on Display page.
        """
        logger.info("Checking brightness slider visibility")
        settings_page.go_to_system_display()
        assert_true(settings_page.is_brightness_slider_visible(), "Brightness slider is not visible")

    def test_night_light_toggle_available(self, settings_page, logger):
        """
        Verify that Night light toggle is displayed on Display page.
        """
        logger.info("Checking Night light toggle presence")
        settings_page.go_to_system_display()
        element = settings_page.find("system_display.night_light_toggle")
        assert_true(element.is_displayed(), "Night light toggle not displayed")

    def test_open_advanced_display_page(self, settings_page, logger):
        """
        Verify that clicking Advanced display link works.
        """
        logger.info("Opening Advanced display page")
        settings_page.go_to_system_display()
        settings_page.click("system_display.advanced_display_link")
        # For now we just assert the click succeeded by checking the element still exists.
        link = settings_page.find("system_display.advanced_display_link")
        assert_true(link is not None, "Advanced display link not clickable or missing")

    def test_scale_dropdown_present(self, settings_page, logger):
        """
        Verify that display Scale dropdown is present.
        """
        logger.info("Verifying Scale dropdown presence")
        settings_page.go_to_system_display()
        element = settings_page.find("system_display.scale_dropdown")
        assert_true(element.is_displayed(), "Scale dropdown not visible on Display page")

    def test_resolution_dropdown_present(self, settings_page, logger):
        """
        Verify that Resolution dropdown is present.
        """
        logger.info("Verifying Resolution dropdown presence")
        settings_page.go_to_system_display()
        element = settings_page.find("system_display.resolution_dropdown")
        assert_true(element.is_displayed(), "Resolution dropdown not visible on Display page")

    @pytest.mark.settings_functional
    def test_toggle_night_light_on_off(self, settings_page, logger):
        """
        Try toggling Night light and verify the element remains interactable.
        (Exact state validation can be wired later to a specific attribute.)
        """
        logger.info("Toggling Night light ON/OFF")
        settings_page.go_to_system_display()
        toggle = settings_page.find("system_display.night_light_toggle")
        settings_page.toggle_night_light()
        assert_true(toggle.is_enabled(), "Night light toggle should remain enabled after first click")
        settings_page.toggle_night_light()
        assert_true(toggle.is_enabled(), "Night light toggle should remain enabled after second click")

    @pytest.mark.settings_functional
    def test_change_brightness_interaction(self, settings_page, logger):
        """
        Interact with brightness slider to ensure it is focusable/clickable.
        """
        logger.info("Interacting with brightness slider")
        settings_page.go_to_system_display()
        slider = settings_page.find("system_display.brightness_slider")
        slider.click()
        assert_true(slider.is_enabled(), "Brightness slider should be enabled for interaction")

    def test_display_page_persists_after_navigation(self, settings_page, logger):
        """
        Open another section and navigate back to System > Display,
        verifying that Display header is still accessible.
        """
        logger.info("Verifying Display page after navigation away and back")
        settings_page.go_to_system_display()
        # Navigate to another root section, then back
        settings_page.go_to_network_home()
        settings_page.go_to_system_display()
        header_text = settings_page.get_text("system_display.header")
        assert_true("Display" in header_text, "Display header not visible after navigating back")

