"""
Tests for Windows Settings - Time & language.
"""

import pytest

from libs.utils.assertions import assert_true


@pytest.mark.settings_navigation
@pytest.mark.time_language
class TestSettingsTimeLanguage:
    """
    Around 10 tests focused on the Time & language section:
    Date & time, Language & region, Typing.
    """

    @pytest.mark.smoke
    def test_navigate_to_time_language_home(self, settings_page, logger):
        """
        Navigate to Time & language home and verify 'Date & time' item.
        """
        logger.info("Navigating to Time & language home")
        settings_page.go_to_time_language_home()
        item = settings_page.find("time_language.date_time_menu_item")
        assert_true(item.is_displayed(), "Date & time menu item not visible on Time & language home")

    def test_open_date_time_page(self, settings_page, logger):
        """
        Open Date & time page and verify header.
        """
        logger.info("Opening Date & time page")
        settings_page.go_to_date_time()
        header = settings_page.get_text("time_language.date_time_header")
        assert_true("Date & time" in header, "Date & time header not visible")

    @pytest.mark.settings_functional
    def test_toggle_set_time_automatically(self, settings_page, logger):
        """
        Toggle 'Set time automatically' to ensure control is clickable.
        """
        logger.info("Toggling 'Set time automatically'")
        settings_page.go_to_date_time()
        settings_page.toggle_set_time_automatically()
        toggle = settings_page.find("time_language.set_time_automatically")
        assert_true(toggle.is_enabled(), "'Set time automatically' toggle should be enabled after click")

    @pytest.mark.settings_functional
    def test_toggle_set_timezone_automatically(self, settings_page, logger):
        """
        Toggle 'Set time zone automatically'.
        """
        logger.info("Toggling 'Set time zone automatically'")
        settings_page.go_to_date_time()
        settings_page.toggle_set_timezone_automatically()
        toggle = settings_page.find("time_language.set_timezone_automatically")
        assert_true(toggle.is_enabled(), "'Set time zone automatically' toggle should be enabled after click")

    def test_time_zone_dropdown_present(self, settings_page, logger):
        """
        Verify time zone dropdown exists on Date & time page.
        """
        logger.info("Checking time zone dropdown presence")
        settings_page.go_to_date_time()
        dropdown = settings_page.find("time_language.time_zone_dropdown")
        assert_true(dropdown.is_displayed(), "Time zone dropdown not visible")

    def test_sync_now_button_present(self, settings_page, logger):
        """
        Verify Sync now button is present and clickable.
        """
        logger.info("Checking 'Sync now' button")
        settings_page.go_to_date_time()
        settings_page.click_sync_now()
        button = settings_page.find("time_language.sync_now_button")
        assert_true(button.is_displayed(), "'Sync now' button not visible after click")

    def test_open_language_region_page(self, settings_page, logger):
        """
        Open Language & region page and verify add language button.
        """
        logger.info("Opening Language & region page")
        settings_page.go_to_language_region()
        add_btn = settings_page.find("time_language.add_language_button")
        assert_true(add_btn.is_displayed(), "'Add language' button not visible on Language & region page")

    def test_preferred_languages_list_visible(self, settings_page, logger):
        """
        Verify preferred languages list is visible on Language & region page.
        """
        logger.info("Checking preferred languages list visibility")
        settings_page.go_to_language_region()
        lang_list = settings_page.find("time_language.preferred_languages_list")
        assert_true(lang_list.is_displayed(), "Preferred languages list not visible")

    def test_open_typing_page(self, settings_page, logger):
        """
        Open Typing page and verify one known control.
        """
        logger.info("Opening Typing settings page")
        settings_page.go_to_typing()
        toggle = settings_page.find("time_language.typing_suggestions_toggle")
        assert_true(toggle.is_displayed(), "Typing suggestions toggle not visible on Typing page")

    @pytest.mark.settings_functional
    def test_toggle_typing_suggestions_and_autocorrect(self, settings_page, logger):
        """
        Toggle typing suggestions and autocorrect switches.
        """
        logger.info("Toggling typing suggestions and autocorrect")
        settings_page.go_to_typing()
        settings_page.toggle_typing_suggestions()
        sugg_toggle = settings_page.find("time_language.typing_suggestions_toggle")
        assert_true(sugg_toggle.is_enabled(), "Typing suggestions toggle should be enabled after click")

        settings_page.toggle_autocorrect()
        auto_toggle = settings_page.find("time_language.autocorrect_toggle")
        assert_true(auto_toggle.is_enabled(), "Autocorrect toggle should be enabled after click")

