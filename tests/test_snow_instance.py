"""
Test that the ServiceNow instance is reachable and that the credentials are correct

"""

import pytest

from playwright.sync_api import Page

from browsergym.workarena.api.system_properties import get_sys_property
from browsergym.workarena.instance import SNowInstance, fetch_instances
from browsergym.workarena.utils import ui_login

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright

INSTANCE_POOL = fetch_instances()

if not INSTANCE_POOL:
    pytest.skip(
        "No ServiceNow instances available from fetch_instances().", allow_module_level=True
    )


@pytest.fixture(
    scope="session", params=INSTANCE_POOL, ids=[entry["url"] for entry in INSTANCE_POOL]
)
def snow_instance_entry(request):
    return request.param


def test_check_is_reachable(snow_instance_entry):
    """
    Test that the ServiceNow instance is reachable

    """
    # Use the first instance from the pool to avoid random selection in the constructor.
    instance = SNowInstance(
        snow_url=snow_instance_entry["url"],
        snow_credentials=("admin", snow_instance_entry["password"]),
    )

    # We modify the URL and ensure that the instance is not reachable
    instance.snow_url = "https://invalid.url"
    # We check that this raises an exception
    with pytest.raises(RuntimeError):
        instance._check_is_reachable()


def test_instance_active(snow_instance_entry, page: Page):
    """
    Test that the ServiceNow instance is active (not hibernating)

    """
    instance = SNowInstance(
        snow_url=snow_instance_entry["url"],
        snow_credentials=("admin", snow_instance_entry["password"]),
    )
    page.goto(instance.snow_url)
    assert (
        "hibernating" not in page.title().lower()
    ), f"Instance {instance.snow_url} is not active. Wake it up by navigating to {instance.snow_url} in a browser."


def test_credentials(snow_instance_entry, page: Page):
    """
    Test that the credentials are correct

    """
    instance = SNowInstance(
        snow_url=snow_instance_entry["url"],
        snow_credentials=("admin", snow_instance_entry["password"]),
    )
    try:
        ui_login(instance=instance, page=page)  # Raises exception if login fails
    except Exception as exc:  # pragma: no cover - adds context for debugging
        pytest.fail(f"Login failed on instance {instance.snow_url}: {exc}")


def test_workarena_installed(snow_instance_entry):
    """
    Test that WorkArena installation is detected via the installation date property.

    """
    instance = SNowInstance(
        snow_url=snow_instance_entry["url"],
        snow_credentials=("admin", snow_instance_entry["password"]),
    )
    installation_date = get_sys_property(
        instance=instance, property_name="workarena.installation.date"
    )
    assert installation_date, f"Instance {instance.snow_url} missing workarena.installation.date."
