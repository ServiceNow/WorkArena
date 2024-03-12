"""
General utiilty functions

"""

import playwright.sync_api

from browsergym.workarena.instance import SNowInstance

from urllib import parse


def impersonate_user(username: str, page: playwright.sync_api.Page):
    """
    Impersonate a user in the ServiceNow interface

    Parameters:
    -----------
    username: str
        The username of the user to impersonate
    page: playwright.sync_api.Page
        The page instance to use for the impersonation (you must be logged in as admin)

    Notes:
    ------
    * If you provide a username that matches to multiple users (e.g., a partial one), the first one will be selected

    """
    page.get_by_label("Avatar: available, user preferences").click()
    page.get_by_role("menuitem", name="Impersonate user").click()
    page.locator("input.now-typeahead-native-input").click()
    page.locator("input.now-typeahead-native-input").fill(username)
    page.locator("seismic-hoist").get_by_role("option", name=username).first.click()
    with page.expect_navigation():
        page.get_by_role("button", name="Impersonate user").click()

    # If there is the analytics dialog, close it
    page.wait_for_load_state("networkidle")
    if page.get_by_label("Close dialog").count() > 0:
        page.keyboard.press("Escape")


def ui_login(instance: SNowInstance, page: playwright.sync_api.Page):
    """
    Log into the instance via the UI

    Parameters:
    -----------
    instance:
        The instance to log into
    page:
        The page instance to use for the UI login

    """
    (snow_username, snow_password) = instance.snow_credentials

    # Navigate to instance
    page.goto(instance.snow_url)

    # If login is required, we'll be redirected to the login page
    if "log in | servicenow" in page.title().lower():
        page.get_by_label("User name").fill(snow_username)
        page.get_by_label("Password", exact=True).fill(snow_password)
        with page.expect_navigation():
            page.get_by_role("button", name="Log in").click()

    # Check if we have been returned to the login page (appends /welcome.do)
    current_url = parse.urlparse(parse.unquote(page.evaluate("() => window.location.href")))
    if current_url.path.endswith("/welcome.do"):
        raise RuntimeError("Login failed.")
