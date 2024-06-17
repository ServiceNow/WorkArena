"""
Tasks related to basic menu navigation.

"""

import json
import playwright.sync_api
import re

from importlib import resources
from playwright.sync_api import Page
from urllib import parse
from typing import List, Tuple

from ..api.utils import table_api_call
from .base import AbstractServiceNowTask
from ..config import ALL_MENU_PATH, IMPERSONATION_CONFIG_PATH
from ..instance import SNowInstance
from ..utils import impersonate_user


class AllMenuTask(AbstractServiceNowTask):
    """
    Navigate to some application module using the All menu.

    Parameters:
    -----------

    instance: SNowInstance
        The instance on which to create the record.
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/all_menu.json
        for an example of a configuration file.

    """

    def __init__(
        self, seed: int = None, instance: SNowInstance = None, fixed_config: dict = None, **kwargs
    ) -> None:
        super().__init__(seed=seed, instance=instance, start_rel_url="/now/nav/ui/home")
        self.fixed_config = fixed_config
        with open(ALL_MENU_PATH, "r") as f:
            self.all_configs = json.load(f)
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get task configuration
        self.module = (
            self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        )

        # When menu tasks do not need to be validated, the URL can be omitted from their config
        self.final_url = self.instance.snow_url + self.module.get("url", "")

        # Generate goal
        goal = f'Navigate to the "{self.module["module"]}" module of the "{self.module["application"]}" application.'
        info = {}

        return goal, info

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        task_info = f'- Navigate to the "{self.module["module"]}" module of the "{self.module["application"]}" application.'

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
        # gsft_main remains undefined on the landing page; we have to wait for the network to be idle instead.
        page.wait_for_load_state("networkidle")
        menu_button = page.locator('div[aria-label="All"]')
        if menu_button.get_attribute("aria-expanded").lower() != "true":
            menu_button.click()

        # Select the menu's main div
        menu = page.locator('div[aria-label="All menu"]')

        # Filter the menu using the application's name
        menu.get_by_placeholder("Filter").fill(self.module["application"])

        # Avoids issues due to list not being fully filtered yet
        # We could certainly do something more fancy, but it's not
        # worth spending time on right now.
        page.wait_for_timeout(1000)

        path = [m.strip() for m in self.module["module"].split(">")]
        # Navigate to the application's location in the menu and select its parent
        locator = menu.get_by_label(self.module["application"], exact=True).and_(
            menu.get_by_role("button")
        )
        locator = locator.locator("xpath=ancestor::div[contains(@class, 'snf-collapsible-list')]")
        for module in path[:-1]:
            # Expand menu if necessary (this is mostly for visual satisfaction, cheat func would still work without it)
            # XXX: Double selector here is due to discrepancies in the UI for various ServiceNow releases
            button = locator.locator(
                f'button[aria-label="{module}"], div[role="button"][aria-label="{module}"]'
            ).first
            button.scroll_into_view_if_needed()
            if button.get_attribute("aria-expanded").lower() != "true":
                button.click()

            # Get the button's parent "collapsible list" container
            parent_div_locator = button.locator(
                "xpath=ancestor::div[contains(@class, 'snf-collapsible-list')]"
            )
            locator = parent_div_locator

        # Click the final menu item
        menu_item = locator.get_by_label(path[-1], exact=True)
        # In some cases, like System Scheduler > Scheduled Jobs > Scheduled Jobs, modules are repeated in the path
        # This causes problems when clicking. Therefore, we pick the last item
        if menu_item.count() > 1:
            menu_item = menu_item.first
        with page.expect_navigation():
            menu_item.click()
        page.wait_for_timeout(2000)

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        page.wait_for_load_state("domcontentloaded")

        # Get the current URL and the final URL
        current_url = parse.urlunparse(
            parse.urlparse(parse.unquote(page.evaluate("() => window.location.href")))
        )
        final_url = parse.urlunparse(parse.urlparse(parse.unquote(self.final_url)))

        if final_url == current_url:
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "Correct module reached."},
            )

        return 0, False, "", {"message": "Not at expected URL."}

    def teardown(self) -> None:
        pass


class ImpersonationTask(AbstractServiceNowTask):
    """
    Task to impersonate a user.

    Parameters:
    -----------

    instance: SNowInstance
        The instance on which to create the record.
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/impersonation_users.json
        for an example of a configuration file.

    """

    def __init__(
        self, seed: int = None, instance=None, fixed_config: dict = None, **kwargs
    ) -> None:
        super().__init__(seed=seed, instance=instance, start_rel_url="/now/nav/ui/home")
        self.fixed_config = fixed_config
        with open(IMPERSONATION_CONFIG_PATH, "r") as f:
            self.all_configs = json.load(f)
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get task configuration
        self.user_full_name = (
            self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        )
        assert self.user_full_name in self.all_configs

        # Generate goal
        goal = f"Impersonate the user {self.user_full_name}."
        info = {}

        return goal, info

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        task_info = f"- Impersonate the user {self.user_full_name} \n"

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
        impersonate_user(self.user_full_name, page)

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        page.wait_for_function("window.NOW && window.NOW.user")

        user_info = page.evaluate("window.NOW")["user"]

        # If the current user is not being impersonated, fail.
        if not user_info["isImpersonating"]:
            return 0, False, "", {"message": "Not currently impersonating a user."}

        # Fetch user's full name from database
        user_fullname = table_api_call(
            instance=self.instance,
            table="sys_user",
            params={
                "sysparm_query": f"sys_id={user_info['userID']}",
                "sysparm_fields": "name",
            },
        )["result"][0]["name"]

        # If the name matches, success.
        if user_fullname == self.user_full_name:
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "Correct user impersonated."},
            )

        # Otherwise, fail.
        return 0, False, "", {"message": "Currently impersonating the wrong user."}

    def teardown(self) -> None:
        pass


__TASKS__ = [AllMenuTask, ImpersonationTask]
