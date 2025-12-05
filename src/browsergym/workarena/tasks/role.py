
import playwright.sync_api
from typing import Tuple, List, Dict, Any
import requests

class ServiceNowRoleTask(AbstractServiceNowTask):
    """
    Generic task for role manipulation (create/edit) in a table using a Glide form.
    """

    def __init__(self, seed: int, config: Dict[str, Any]) -> None:
        super().__init__(seed)
        self.task_is_setup = False
        self.config = config
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
            return 0
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
                return 0
        return 1

    def teardown(self) -> None:
        # TODO: implement this (delete role for users)
        pass