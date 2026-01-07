import json
from typing import Any, Dict, List, Tuple
import re
import playwright.sync_api
import requests
from urllib import parse
from ..api.utils import HTTPError, db_delete_from_table
from ..config import (
    ASSIGN_ROLE_TO_USER_ADMIN_CONFIG_PATH,
    ASSIGN_ROLES_TO_USER_EXPLICIT_CONFIG_PATH,
    ASSIGN_ROLES_TO_USER_IMPLICIT_CONFIG_PATH,
)
from .base import AbstractServiceNowTask


class ServiceNowRoleTask(AbstractServiceNowTask):
    """
    Generic task for role manipulation (create/edit) in a table using a Glide form.
    """

    def __init__(self, seed: int, fixed_config: Dict[str, Any] = None, start_rel_url: str = "/now/nav/ui/home") -> None:
        super().__init__(seed, start_rel_url=start_rel_url)
        self.task_is_setup = False
        self.config = fixed_config if fixed_config else self.random.choice(self.all_configs())
        self.timeout = 60000
        self.created_sysids = []

    def setup_goal(self, page: playwright.sync_api.Page) -> Tuple[str, dict]:
        """Setup the task configuration and produce the goal."""

        goal = self.config["goal"]
        info = self.config

        return goal, info

    def cheat(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
        self._url_login(page)
        self._navigate_to_page(page, "sys_user.list")
        self._search_for_user(page, self.config["user_full_name"])
        self._open_user_page(page, self.config["user_full_name"])
        self._open_user_roles_page(page)
        self._assign_roles(page, self.config.get("roles", "admin"))

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        # get relevant info from config
        user_full_name = self.config["user_full_name"]
        user_roles = self.config.get("roles", "admin")
        user_roles = [role.strip() for role in user_roles.split(",")]

        # query instance to get user sys id
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/sys_user",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"name={user_full_name}",
                "sysparm_fields": "sys_id",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        record = response.json().get("result", [])
        if not record:
            return (
                0,
                False,
                "",
                {"message": "The user was not found."},
            )
        user_sys_id = record[0]["sys_id"]

        # query sys_user_has_role to find user roles
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/sys_user_has_role",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"user={user_sys_id}",
                "sysparm_display_value": "all",
                "sysparm_fields": "sys_id,role",
                "sysparm_limit": 200,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        role_to_sys_id_mapping = {elem["role"]["display_value"]: elem["sys_id"] for elem in result}
        for role in user_roles:
            if not role in role_to_sys_id_mapping:
                return (
                    0,
                    False,
                    "",
                    {"message": "The role does not match."},
                )
            else:
                self.created_sysids.append(role_to_sys_id_mapping[role])
        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The record was successfully edited."},
        )

    def teardown(self) -> None:

        # go over all created sysids and delete that record in the sys_user_has_role table
        for sys_id in self.created_sysids:
            if sys_id is not None:
                try:
                    db_delete_from_table(instance=self.instance, sys_id=sys_id, table="sys_user_has_role")
                except HTTPError:
                    # sys_id was stored in local storage (for submitted)
                    # but the record is absent from the database (probably invalid form)
                    pass

    def all_configs(self):
        raise NotImplementedError

    def _url_login(self, page):
        (snow_username, snow_password) = self.instance.snow_credentials

        # Encode special characters
        snow_username = parse.quote(snow_username)
        snow_password = parse.quote(snow_password)

        # Log in via URL
        page.goto(f"{self.instance.snow_url}/login.do?user_name={snow_username}&user_password={snow_password}&sys_action=sysverb_login")

        # Check if we have been returned to the login page
        current_url = parse.urlparse(parse.unquote(page.evaluate("() => window.location.href")))
        if "login.do" in current_url.path:
            raise RuntimeError("Login failed. Check credentials and make sure to have run installer.")

    def _navigate_to_page(self, page, page_name: str = "sys_user.list"):
        # gsft_main remains undefined on the landing page; we have to wait for the network to be idle instead.
        page.wait_for_load_state("networkidle")
        menu_button = page.locator('div[aria-label="All"]')
        if (menu_button.get_attribute("aria-expanded")).lower() != "true":
            menu_button.click()

        # Select the menu's main div
        menu = page.locator('div[aria-label="All menu"]')

        # Filter the menu using the application's name
        menu.get_by_placeholder("Filter").fill(page_name)
        page.keyboard.press("Enter")

        # Avoids issues due to list not being fully filtered yet
        # We could certainly do something more fancy, but it's not
        # worth spending time on right now.
        page.wait_for_timeout(5_000)
        page.wait_for_load_state("networkidle")

    def _search_for_user(self, page, user_name: str):
        # focus on iframe
        iframe = page.frame("gsft_main")

        # select "Name" on the dropdown to filter users
        select = iframe.get_by_role("listbox", name="Search a specific field of the Users list")
        select.wait_for(state="visible")
        select.select_option(value="name")

        # enter name in input
        search_field = iframe.locator('input[aria-label="Search"]')
        search_field.fill(user_name)
        search_field.press("Enter")

        # wait for the user to be loaded
        page.wait_for_load_state("networkidle")

    def _open_user_page(self, page, user_name: str):
        iframe = page.frame("gsft_main")

        pattern = re.compile(rf"Open record:\s*{re.escape(user_name)}", re.IGNORECASE)

        # find element with aria label containing "Open record: {user_name}"
        record_link = iframe.get_by_role("link", name=pattern)
        record_link.click()

    def _open_user_roles_page(self, page):
        iframe = page.frame("gsft_main")

        # find tab with name "Roles"
        pattern = re.compile(rf"Roles*", re.IGNORECASE)
        tab_button = iframe.get_by_role("tab", name=pattern)
        tab_button.click()

        # click on "Edit... "
        edit_button = iframe.get_by_role("button", name="Edit...")
        edit_button.click()

    def _assign_roles(self, page, roles: List[str]):
        iframe = page.frame("gsft_main")
        for role in roles:

            # click on option with name "role"
            option = iframe.get_by_role("option", name=role, exact=True)
            option.click()

            # click on arrow pointing right
            add_button = iframe.get_by_role("button", name="Add selected options")
            add_button.dblclick()

        # click on submit button
        save_button = iframe.locator('button[type="submit"]').filter(has_text="Save").first
        save_button.click()

class AssignRoleToUserAdminTask(ServiceNowRoleTask):
    def all_configs(self):
        return json.load(open(ASSIGN_ROLE_TO_USER_ADMIN_CONFIG_PATH))


class AssignRolesToUserImplicitTask(ServiceNowRoleTask):
    def all_configs(self):
        return json.load(open(ASSIGN_ROLES_TO_USER_IMPLICIT_CONFIG_PATH))


class AssignRolesToUserExplicitTask(ServiceNowRoleTask):
    def all_configs(self):
        return json.load(open(ASSIGN_ROLES_TO_USER_EXPLICIT_CONFIG_PATH))


__TASKS__ = [AssignRoleToUserAdminTask, AssignRolesToUserImplicitTask, AssignRolesToUserExplicitTask]
