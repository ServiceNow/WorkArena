import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

from ..api.utils import HTTPError, table_api_call, db_delete_from_table
from ..config import DEACTIVATE_USER_GROUP_CONFIG_PATH, CREATE_USER_GROUP_CONFIG_PATH, CREATE_USER_GROUP_ADD_USERS_CONFIG_PATH
from .base import AbstractServiceNowTask


class ServiceNowUserGroupTask(AbstractServiceNowTask):

    def __init__(self, seed: int, fixed_config: Dict[str, Any] = None, start_rel_url: str = "/now/nav/ui/home") -> None:
        super().__init__(seed, start_rel_url=start_rel_url)
        self.task_is_setup = False
        self.config = fixed_config if fixed_config else self.random.choice(self.all_configs())
        self.timeout = 60000
        self.created_sysids = []

        self.user_group_sys_id = None

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

    def all_configs(self):
        return json.load(open(CREATE_USER_GROUP_CONFIG_PATH))

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        
        # verify whether a group with the name exists
        result = table_api_call(
            instance=self.instance,
            table="sys_user_group",
            params={
                "sysparm_query": f"nameSTARTSWITH{self.config['name']}",
                # "sysparm_fields": "number",
                "sysparm_limit": 1,
                "sysparm_display_value": "true",
            },
        )["result"]

        if not result:
            return (
                0,
                False,
                "",
                {"message": "The user group was not found."},
            )

        self.user_group_sys_id = result[0]["sys_id"]

        # check whether manager is right
        if result[0]["manager"]["display_value"] != self.config["manager"]:
            return (
                0,
                False,
                "",
                {"message": "The manager is not correct."},
            )

        # check whether type is right
        if result[0]["type"] != self.config["type"]:
            return (
                0,
                False,
                "",
                {"message": "The type is not correct."},
            )

        # check whether roles are right
        if result[0]["roles"] != self.config["roles"]:
            return (
                0,
                False,
                "",
                {"message": "The roles are not correct."},
            )

        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The user group was successfully created."},
        )

    def teardown(self) -> None:
        try:
            db_delete_from_table(
                instance=self.instance,
                table="sys_user_group",
                sys_id=self.user_group_sys_id,
            )
        except HTTPError:
            pass

class CreateUserGroupAddUsersTask(CreateUserGroupTask):
    # reusing the teardown from CreateUserGroupTask

    def all_configs(self):
        return json.load(open(CREATE_USER_GROUP_ADD_USERS_CONFIG_PATH))
    
    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        
        # verify whether a group with the name exists
        result = table_api_call(
            instance=self.instance,
            table="sys_user_group",
            params={
                "sysparm_query": f"nameSTARTSWITH{self.config['name']}",
                # "sysparm_fields": "number",
                "sysparm_limit": 1,
                "sysparm_display_value": "true",
            },
        )["result"]

        if not result:
            return (
                0,
                False,
                "",
                {"message": "The user group was not found."},
            )

        self.user_group_sys_id = result[0]["sys_id"]

        # check whether description is right
        if result[0]["description"] != self.config["description"]:
            return (
                0,
                False,
                "",
                {"message": "The description is not correct."},
            )

        # check members
        result = table_api_call(
            instance=self.instance,
            table="sys_user_grmember",
            params={
                "sysparm_query": f"user_group={self.user_group_sys_id}",
                "sysparm_display_value": "true",
            },
        )["result"]
        group_members = sorted(list(set([member["user"]["display_value"] for member in result])))
        ground_truth_group_members = sorted(list(set([elem.strip() for elem in self.config["members"].split(",")])))

        if group_members != ground_truth_group_members:
            return (
                0,
                False,
                "",
                {"message": "The members are not correct."},
            )

        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The user group was successfully created."},
        )
    


class DeactivateUserGroupTask(ServiceNowUserGroupTask):

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
            requests.patch(
                f"{self.instance.snow_url}/api/now/table/sys_user_group/{self.user_group_sys_id}",
                auth=self.instance.snow_credentials,
                headers={"Accept": "application/json"},
                json={
                    "active": True,
                },
            )
        except HTTPError:
            pass


__TASKS__ = [
    DeactivateUserGroupTask,
    CreateUserGroupTask,
    CreateUserGroupAddUsersTask,
]
