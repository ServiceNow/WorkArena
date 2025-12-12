import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

from ..api.utils import HTTPError, table_api_call
from ..config import DEACTIVATE_USER_GROUP_CONFIG_PATH
from .base import AbstractServiceNowTask


class ServiceNowUserGroupTask(AbstractServiceNowTask):

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

    def all_configs(self):
        raise NotImplementedError


class CreateUserGroupTask(ServiceNowUserGroupTask):
    pass


class DeactivateUserGroupTask(ServiceNowUserGroupTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user_group_sys_id = None

    def all_configs(self):
        return json.load(open(DEACTIVATE_USER_GROUP_CONFIG_PATH))

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        name = self.config["name"]

        # Query sn_customerservice_case in ServiceNow
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/sys_user_group",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"name={name}",
                "sysparm_fields": "sys_id,name,active",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            return (
                0,
                False,
                "",
                {"message": "The user group was not found."},
            )
        self.user_group_sys_id = result[0]["sys_id"]

        # check for active
        if not result[0]["active"]:
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "The user group was successfully deactivated."},
            )
        return (
            0,
            False,
            "",
            {"message": "The user group was not deactivated."},
        )

    def teardown(self) -> None:
        try:
            table_api_call(
                instance=self.instance,
                table="sys_user_group",
                params={
                    "sysparm_query": f"sys_id={self.user_group_sys_id}",
                    "sysparm_limit": 1,
                },
                method="PUT",
                data={"active": True},
            )
        except HTTPError:
            pass


__TASKS__ = [
    DeactivateUserGroupTask,
]
