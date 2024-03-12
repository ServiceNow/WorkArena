"""
Test that the ServiceNow instance is reachable and that the credentials are correct

"""

import pytest

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright

from playwright.sync_api import Page

from browsergym.workarena.instance import SNowInstance
from browsergym.workarena.utils import ui_login


def test_check_is_reachable():
    """
    Test that the ServiceNow instance is reachable

    """
    # This tests that the user's config is correct
    # If it is not, the creation of the instance object
    # will simply return an exception
    instance = SNowInstance()

    # We modify the URL and ensure that the instance is not reachable
    instance.snow_url = "https://invalid.url"
    # We check that this raises an exception
    with pytest.raises(RuntimeError):
        instance._check_is_reachable()


def test_instance_active(page: Page):
    """
    Test that the ServiceNow instance is active (not hibernating)

    """
    instance = SNowInstance()
    page.goto(instance.snow_url)
    assert (
        "hibernating" not in page.title().lower()
    ), f"Instance is not active. Wake it up by navigating to {instance.snow_url} in a browser."


def test_credentials(page: Page):
    """
    Test that the credentials are correct

    """
    instance = SNowInstance()
    ui_login(instance=instance, page=page)  # Raises exception if login fails
