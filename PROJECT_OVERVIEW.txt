QAMA Windows Settings Automation Framework
==========================================

1. Purpose
----------

This project automates the Windows Settings application using:
- Pytest as the test runner
- Selenium + Appium Python Client v3 (Windows Driver)
- Page Object Model (POM)
- A QAMA-style folder structure with a JSON-based UI map

The main goal is to provide a clean, extensible framework where you can:
- Add new Settings features (modules) quickly
- Centralize locators in a JSON file
- Use pytest markers to run targeted suites and generate HTML reports


2. High-Level Architecture
--------------------------

Top-level structure:

- config/               : Runtime configuration (YAML)
- libs/                 : Framework code (drivers, POM, utils)
- resource/ui_map/      : JSON locator map for Windows Settings
- tests/                : All pytest tests and fixtures
- requirements.txt      : Python dependencies
- .gitignore            : Git ignore rules

The tests call Page Objects (POM) which use the BasePage to read locators
from the JSON UI map and drive the Windows Settings app via the Appium
Windows driver.


3. Folder-by-Folder Details
---------------------------

3.1 config/
-----------

File: config.yaml

Contains:

- Top-level WinAppDriver defaults:
  - winappdriver:
    - server_url   : URL of the Appium server (e.g. http://127.0.0.1:4723)
    - platformName : "Windows"
    - deviceName   : "WindowsPC"

- Module-specific configuration for Windows Settings:
  - modules:
      settings:
        app:
          app_id : "SystemSettings" (AppId for Settings)
        winappdriver:
          server_url   : (optional override, falls back to top-level)
          deviceName   : (optional override)
          platformName : (optional override)
        timeouts:
          implicit_wait_sec       : Default implicit wait for driver
          new_command_timeout_sec : Timeout for driver commands
        resources:
          ui_map: "resource/ui_map/windows/settings.json"

This file is consumed primarily by libs/drivers/windows_driver.py.


3.2 libs/drivers/
-----------------

Purpose: Isolate all driver/session creation logic.

3.2.1 windows_driver.py
-----------------------
Key responsibilities:
- Load config/config.yaml
- Read top-level winappdriver defaults and the modules.settings section
- Initialize a singleton Appium Remote WebDriver session with:
  - platformName              (from module override or top-level)
  - deviceName                (from module override or top-level)
  - app_id for Settings       (mapped to capability "appium:app")
  - new_command_timeout_sec   (mapped to capability "appium:newCommandTimeout")
- Expose:
  - WindowsDriver.get_driver() : returns the singleton driver instance
  - WindowsDriver.quit_driver(): quits the driver and clears the singleton

The driver also configures the implicit wait using
modules.settings.timeouts.implicit_wait_sec.

3.2.2 app_session.py
--------------------
Small facade over WindowsDriver. Provides:
- AppSession.start() : calls WindowsDriver.get_driver()
- AppSession.stop()  : calls WindowsDriver.quit_driver()

Tests and fixtures should depend on AppSession, not on WindowsDriver directly.


3.3 libs/utils/
---------------

Helper utilities shared across the framework.

3.3.1 base_page.py (POM base class)
-----------------------------------

Responsibilities:
- Load the UI map JSON from:
  resource/ui_map/windows/settings.json
- Keep full JSON in self._ui_map
- Focus on self._locators = self._ui_map["locators"]
- Resolve dotted locator keys such as:
  - "system_display.brightness_slider"
  - "time_language.date_time_menu_item"
  - "personalization.background_preview"

Expected JSON structure (matching the calculator sample you provided):

{
  "app": { ... },
  "locators": {
    "system_display": {
      "brightness_slider": { "locator": { "AutomationID": "BrightnessSlider" } }
    }
  },
  "testdata": { ... }
}

Locator resolution rules:
- "AutomationID" -> By.ACCESSIBILITY_ID
- "name"        -> By.NAME
- "xpath"       -> By.XPATH
- "id"          -> By.ID

Public methods:
- find(key_path)      : Returns WebElement
- click(key_path)     : Waits for visibility, then click()
- get_text(key_path)  : Waits for visibility, then returns .text

3.3.2 waits.py
--------------
Thin wrappers around WebDriverWait / expected_conditions:
- wait_for(driver, condition, timeout)
- wait_for_element_present(driver, locator, timeout)
- wait_for_element_visible(driver, locator, timeout)

3.3.3 assertions.py
-------------------
Custom assertion helpers:
- assert_equal(actual, expected, message=None)
- assert_true(condition, message=None)
- assert_false(condition, message=None)

These helpers give clearer error messages and cleaner test code.

3.3.4 logger.py
---------------
Configures the framework logger:
- Creates logs/ directory
- File + console handlers with timestamp + level + message
- get_logger("QAMA") is used by the pytest logger fixture.


3.4 libs/flows/windows/
-----------------------

3.4.1 settings_page.py (SettingsPage)
-------------------------------------

This is the central Page Object for the Windows Settings app.

Initialization:
- SettingsPage(driver) -> BasePage(driver, "settings.json")

Core methods:
- is_loaded():
  - Returns True if the System tab ("nav.system_tab") is visible.

Navigation helpers:
- go_to_system_display()
- go_to_time_language_home()
- go_to_date_time()
- go_to_language_region()
- go_to_typing()
- go_to_personalization_home()
- go_to_personalization_background()
- go_to_personalization_themes()
- go_to_personalization_colors()
- go_to_personalization_lock_screen()
- go_to_personalization_start()
- go_to_personalization_taskbar()

Feature-specific actions:

System > Display
- is_brightness_slider_visible()
- toggle_night_light()

Time & language
- toggle_set_time_automatically()
- toggle_set_timezone_automatically()
- click_sync_now()
- toggle_typing_suggestions()
- toggle_autocorrect()

Personalization
- toggle_dark_mode()
- toggle_light_mode()
- toggle_start_recent_apps()
- toggle_taskbar_auto_hide()

Tests do not know about locators; they work purely through these methods and
high-level find/click/get_text from the base page.


3.5 resource/ui_map/windows/settings.json
-----------------------------------------

Single source of truth for all locators and some test data.

Top-level structure:
- "app"      : info about the Settings app window
- "locators" : all UI elements used by the POM and tests
- "testdata" : sample values (e.g., brightness settings, themes)

locators.nav:
- system_tab
- time_language_tab
- personalization_tab
- back_button
- home_button

locators.system_display:
- display_menu_item
- header
- brightness_slider
- night_light_toggle
- scale_dropdown
- resolution_dropdown
- advanced_display_link

locators.time_language:
- date_time_menu_item
- date_time_header
- set_time_automatically
- set_timezone_automatically
- change_date_time_button
- time_zone_dropdown
- sync_now_button
- language_region_menu_item
- add_language_button
- preferred_languages_list
- typing_menu_item
- typing_suggestions_toggle
- autocorrect_toggle

locators.personalization:
- background_menu_item
- background_preview
- background_type_dropdown
- theme_menu_item
- active_theme_label
- colors_menu_item
- dark_mode_radio
- light_mode_radio
- accent_color_picker
- lock_screen_menu_item
- lock_screen_background_combo
- start_menu_item
- start_recent_apps_toggle
- taskbar_menu_item
- taskbar_auto_hide_toggle

testdata:
- brightness_values : [25, 50, 75]
- scales            : ["100%", "125%"]
- themes            : ["Windows (light)", "Windows (dark)"]


3.6 tests/
----------

3.6.1 conftest.py
-----------------

Central pytest configuration:

- Path setup:
  - Adds project root to sys.path so libs.* imports work.

- Fixtures:
  - logger (session):
    - Returns a shared logger from libs.utils.logger.

  - driver (session):
    - Logs test session start/end.
    - Calls AppSession.start() -> creates Appium Windows driver.
    - Yields the driver to tests.
    - Calls AppSession.stop() at the end of the session.

  - settings_page (function):
    - Returns a new SettingsPage(driver) for each test.

- Markers (for filtering tests and suites):
  - smoke
  - regression
  - settings_navigation
  - settings_functional
  - system_display
  - time_language
  - personalization

- Reports folder:
  - pytest_configure() ensures that a "reports" directory exists so
    pytest-html can write HTML reports there.

- HTML report title:
  - pytest_html_report_title() sets the title:
    "QAMA - Windows Settings Automation Report"


3.6.2 tests/modules/settings/
-----------------------------

Feature-based test modules (10 tests each, total 30).

1. test_settings_system_display.py
   - Class: TestSettingsSystemDisplay
   - Marks: @pytest.mark.settings_navigation, @pytest.mark.system_display
   - Covers:
     - App launch and System > Display navigation
     - Brightness slider visibility and interaction
     - Night light toggle presence and clickability
     - Scale and resolution dropdowns presence
     - Advanced display link click
     - Verifies Display page still works after navigating away and back

2. test_settings_time_language.py
   - Class: TestSettingsTimeLanguage
   - Marks: @pytest.mark.settings_navigation, @pytest.mark.time_language
   - Covers:
     - Time & language home and Date & time header
     - Set time automatically toggle
     - Set time zone automatically toggle
     - Time zone dropdown
     - Sync now button
     - Language & region page and Add language button
     - Preferred languages list
     - Typing page and toggles for typing suggestions and autocorrect

3. test_settings_personalization.py
   - Class: TestSettingsPersonalization
   - Marks: @pytest.mark.settings_navigation, @pytest.mark.personalization
   - Covers:
     - Personalization home and Background menu item
     - Background preview and background type dropdown
     - Themes page and active theme label
     - Colors page with dark/light mode radios and accent color picker
     - Lock screen background combo
     - Start "recent apps" toggle
     - Taskbar auto-hide toggle


4. Dependencies and Setup
-------------------------

File: requirements.txt

Dependencies:
- pytest==8.0.0
- selenium==4.18.0
- Appium-Python-Client==3.0.0
- PyYAML==6.0.2
- pytest-html==4.1.1

Install:

    pip install -r requirements.txt


5. Running the Tests
--------------------

Prerequisite:
- Start Appium server with Windows Driver plugin at the URL defined in
  config/config.yaml (by default http://127.0.0.1:4723).

Examples:

5.1 Run all tests (30 cases) with an HTML report:

    pytest tests/modules/settings \
      --html=reports/all_settings.html --self-contained-html


5.2 Run only System > Display tests with a dedicated report:

    pytest -m system_display \
      tests/modules/settings/test_settings_system_display.py \
      --html=reports/system_display.html --self-contained-html


5.3 Run only Time & language tests:

    pytest -m time_language \
      tests/modules/settings/test_settings_time_language.py \
      --html=reports/time_language.html --self-contained-html


5.4 Run only Personalization tests:

    pytest -m personalization \
      tests/modules/settings/test_settings_personalization.py \
      --html=reports/personalization.html --self-contained-html


5.5 Run only smoke tests across all features:

    pytest -m smoke \
      --html=reports/smoke.html --self-contained-html


6. Extending the Framework
--------------------------

To add a new Settings feature:

1) Add locators to settings.json:
   - Under "locators", create a new section, e.g. "privacy".
   - Follow the existing locator format with "locator": { "AutomationID": "..."} or {"name": "..."}.

2) Extend SettingsPage:
   - Add navigation + action methods that reference the new locator keys, e.g.:
     - self.click("privacy.camera_toggle")

3) Add tests:
   - Create a new module under tests/modules/settings/, e.g.
     test_settings_privacy.py
   - Use the settings_page fixture and new POM methods.
   - Add a new marker in pytest_configure(), e.g. "privacy".
   - Decorate the test class or functions with @pytest.mark.privacy.

4) Run tests with a new report:
   - pytest -m privacy --html=reports/privacy.html --self-contained-html


7. Summary
----------

This framework gives you:
- A clean QAMA-compliant structure
- Appium + Selenium-based automation of Windows Settings
- Page Object Model driven by a JSON UI map
- 30 sample test cases split across three core Settings features
- Pytest markers for flexible, category-based execution
- HTML reporting via pytest-html with auto-created reports directory

You can now adjust locators to match your target environment, expand the
Page Object with more features, and keep adding new test modules as needed.

