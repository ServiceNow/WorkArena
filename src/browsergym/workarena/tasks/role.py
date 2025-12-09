import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

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

    def setup_goal(self, page: playwright.sync_api.Page) -> Tuple[str, dict]:
        """Setup the task configuration and produce the goal."""

        goal = self.config["goal"]
        info = self.config

        return goal, info

    def cheat(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> None:
        pass

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        # get relevant info from config
        user_full_name = self.config["user_full_name"]
        user_roles = self.config.get("roles", "admin")
        user_roles = [role.strip() for role in user_roles.split(",")]

        # get instance url and credentials
        instance_url = self.instance.snow_url
        snow_username, snow_password = self.instance.snow_credentials

        # query instance to get user sys id
        response = requests.get(
            f"{instance_url}/api/now/table/sys_user",
            auth=(snow_username, snow_password),
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
            f"{instance_url}/api/now/table/sys_user_has_role",
            auth=(snow_username, snow_password),
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"user={user_sys_id}",
                "sysparm_display_value": "all",
                "sysparm_fields": "role",
                "sysparm_limit": 200,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        roles = [elem["role"]["display_value"] for elem in result]
        for role in user_roles:
            if not role in roles:
                return (
                    0,
                    False,
                    "",
                    {"message": "The role does not match."},
                )
        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The record was successfully edited."},
        )

    def teardown(self) -> None:

        # go over all roles in sys_user_has_role and remove them for the given users
        pass

    def all_configs(self):
        raise NotImplementedError


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
