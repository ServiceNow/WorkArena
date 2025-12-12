
import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

from ..api.utils import HTTPError, table_api_call
from ..config import (
    CHANGE_CHANGE_REQUEST_APPROVER_CONFIG_PATH,
)
from .base import AbstractServiceNowTask


class ServiceNowChangeRequestTask(AbstractServiceNowTask):

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

class ChangeChangeRequestApproverTask(ServiceNowChangeRequestTask):
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.change_request_sys_id = self._get_change_request_sys_id(self.config["change_number"])
        self.change_request_approver_sys_id = None
        self.initial_change_request_approver_state = self._get_initial_change_request_approver_state()

    def _get_initial_change_request_approver_state(self) -> str:
        approvers = self._get_change_request_approvers_list(self.change_request_sys_id)
        for approver in approvers:
            if approver["approver"]["display_value"] == self.config["approver"]:
                return approver["state"]
        raise ValueError(f"Approver {self.config['approver']} not found for change request {self.config['change_number']}")

    def _get_change_request_sys_id(self, change_number: str) -> str:
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/change_request",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={change_number}",
                "sysparm_fields": "sys_id,active",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            raise ValueError(f"Change request {change_number} not found")
        return result[0]["sys_id"]

    def _get_change_request_approvers_list(self, change_request_sys_id: str) -> List[str]:

        # list approvers for change request
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/sysapproval_approver",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"sysapproval={change_request_sys_id}",
                "sysparm_fields": "sys_id,approver,state",
                "sysparm_display_value": "true",
                "sysparm_limit": 100,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        return result

    def all_configs(self):
        return json.load(open(CHANGE_CHANGE_REQUEST_APPROVER_CONFIG_PATH))

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        try:
            approvers_list = self._get_change_request_approvers_list(self.change_request_sys_id)
        except ValueError:
            return (
                0,
                False,
                "",
                {"message": "The approvers for the change request were not found."},
            )

        for row in approvers_list:
            if row["approver"]["display_value"] == self.config["approver"] and row["state"] == "Requested":
                self.change_request_approver_sys_id = row["sys_id"]
                return (
                    1,
                    True,
                    "Nice work, thank you!",
                    {"message": "The change request approver state was successfully changed."},
                )

        return (
            0,
            False,
            "",
            {"message": "The change request approver state was not changed."},
        )


    def teardown(self) -> None:
        # revert the change request approver state to the initial state
        if self.change_request_approver_sys_id is not None:
            try:
                table_api_call(
                    instance=self.instance,
                    table="sysapproval_approver",
                    params={
                        "sysparm_query": f"sys_id={self.change_request_approver_sys_id}",
                        "sysparm_limit": 1,
                    },
                    method="PUT",
                    data={"state": self.initial_change_request_approver_state},
                )
            except HTTPError:
                pass
            

__TASKS__ = [
    ChangeChangeRequestApproverTask,
]