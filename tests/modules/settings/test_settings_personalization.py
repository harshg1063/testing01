"""
Tests for Windows Settings - Personalization.
"""

import pytest

from libs.utils.assertions import assert_true


@pytest.mark.settings_navigation
@pytest.mark.personalization
class TestSettingsPersonalization:
    """
    Around 10 tests focused on the Personalization section:
    Background, Themes, Colors, Lock screen, Start, Taskbar.
    """

    @pytest.mark.smoke
    def test_navigate_to_personalization_home(self, settings_page, logger):
        """
        Navigate to Personalization home and verify basic element.
        """
        logger.info("Navigating to Personalization home")
        settings_page.go_to_personalization_home()
        background_item = settings_page.find("personalization.background_menu_item")
        assert_true(background_item.is_displayed(), "Background menu item not visible on Personalization home")

    def test_background_preview_visible(self, settings_page, logger):
        """
        Open Background settings and ensure preview is visible.
        """
        logger.info("Checking background preview visibility")
        settings_page.go_to_personalization_background()
        preview = settings_page.find("personalization.background_preview")
        assert_true(preview.is_displayed(), "Background preview not visible")

    def test_background_type_dropdown_present(self, settings_page, logger):
        """
        Verify background type drop-down is present on Background page.
        """
        logger.info("Verifying background type drop-down presence")
        settings_page.go_to_personalization_background()
        dropdown = settings_page.find("personalization.background_type_dropdown")
        assert_true(dropdown.is_displayed(), "Background type dropdown not visible")

    def test_themes_page_active_theme_label(self, settings_page, logger):
        """
        Navigate to Themes and verify that active theme label is shown.
        """
        logger.info("Navigating to Themes page")
        settings_page.go_to_personalization_themes()
        label = settings_page.find("personalization.active_theme_label")
        assert_true(label.is_displayed(), "Active theme label not visible on Themes page")

    @pytest.mark.settings_functional
    def test_switch_to_dark_mode(self, settings_page, logger):
        """
        Navigate to Colors and click Dark mode radio.
        """
        logger.info("Switching to dark mode")
        settings_page.go_to_personalization_colors()
        settings_page.toggle_dark_mode()
        dark_radio = settings_page.find("personalization.dark_mode_radio")
        assert_true(dark_radio.is_displayed(), "Dark mode radio button not visible after click")

    @pytest.mark.settings_functional
    def test_switch_to_light_mode(self, settings_page, logger):
        """
        Navigate to Colors and click Light mode radio.
        """
        logger.info("Switching to light mode")
        settings_page.go_to_personalization_colors()
        settings_page.toggle_light_mode()
        light_radio = settings_page.find("personalization.light_mode_radio")
        assert_true(light_radio.is_displayed(), "Light mode radio button not visible after click")

    def test_accent_color_picker_visible(self, settings_page, logger):
        """
        Verify that accent color picker is present on Colors page.
        """
        logger.info("Checking accent color picker visibility")
        settings_page.go_to_personalization_colors()
        picker = settings_page.find("personalization.accent_color_picker")
        assert_true(picker.is_displayed(), "Accent color picker not visible")

    def test_lock_screen_background_combo_present(self, settings_page, logger):
        """
        Navigate to Lock screen and verify background combo/dropdown exists.
        """
        logger.info("Navigating to Lock screen settings")
        settings_page.go_to_personalization_lock_screen()
        combo = settings_page.find("personalization.lock_screen_background_combo")
        assert_true(combo.is_displayed(), "Lock screen background combo not visible")

    @pytest.mark.settings_functional
    def test_start_recent_apps_toggle(self, settings_page, logger):
        """
        Navigate to Start settings and click 'Show recently added apps' toggle.
        """
        logger.info("Toggling 'Show recently added apps' on Start page")
        settings_page.go_to_personalization_start()
        settings_page.toggle_start_recent_apps()
        toggle = settings_page.find("personalization.start_recent_apps_toggle")
        assert_true(toggle.is_enabled(), "Start recent apps toggle should be enabled after click")

    @pytest.mark.settings_functional
    def test_taskbar_auto_hide_toggle(self, settings_page, logger):
        """
        Navigate to Taskbar settings and toggle 'Automatically hide taskbar'.
        """
        logger.info("Toggling taskbar auto-hide")
        settings_page.go_to_personalization_taskbar()
        settings_page.toggle_taskbar_auto_hide()
        toggle = settings_page.find("personalization.taskbar_auto_hide_toggle")
        assert_true(toggle.is_enabled(), "Taskbar auto-hide toggle should be enabled after click")

