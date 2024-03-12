import pytest

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright

from playwright.sync_api import Page

from browsergym.workarena.instance import SNowInstance
from browsergym.workarena.utils import ui_login


def test_ui_login_correct_credentials(page: Page):
    """
    Test logging into the instance via the UI with the correct credentials

    """
    # Log in with correct credentials
    instance = SNowInstance()
    ui_login(instance=instance, page=page)


def test_ui_login_wrong_credentials(page: Page):
    """
    Test logging into the instance via the UI with the wrong credentials

    """
    # Log in with wrong credentials
    instance = SNowInstance(snow_credentials=("wrong", "wrong"))
    with pytest.raises(RuntimeError):
        ui_login(instance=instance, page=page)
