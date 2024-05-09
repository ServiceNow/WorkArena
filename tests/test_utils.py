import pytest

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright

from playwright.sync_api import Page

from browsergym.workarena.instance import SNowInstance
from browsergym.workarena.utils import ui_login, url_login


@pytest.mark.parametrize("login_func", [ui_login, url_login])
def test_login_correct_credentials(login_func, page: Page):
    """
    Test logging into the instance with the correct credentials

    """
    # Log in with correct credentials
    instance = SNowInstance()
    login_func(instance=instance, page=page)


@pytest.mark.parametrize("login_func", [ui_login, url_login])
def test_login_wrong_credentials(login_func, page: Page):
    """
    Test logging into the instance with the wrong credentials

    """
    # Log in with wrong credentials
    instance = SNowInstance(snow_credentials=("wrong", "wrong"))
    with pytest.raises(RuntimeError):
        login_func(instance=instance, page=page)
