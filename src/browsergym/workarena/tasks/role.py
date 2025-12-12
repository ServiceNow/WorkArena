import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

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
        pass

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
            else:
                # find which row from result is associated with that role, get sys_id, and save
                sys_id = next((elem["sys_id"] for elem in result if elem["role"]["display_value"] == role), None)
                self.created_sysids.append(sys_id)
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
