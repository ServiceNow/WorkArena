import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

from ..api.utils import HTTPError, table_api_call
from ..config import (
    CHANGE_RITM_STATUS_CONFIG_PATH,
    UPDATE_RITM_QUANTITY_CONFIG_PATH,
)
from .base import AbstractServiceNowTask


class ServiceNowRitmTask(AbstractServiceNowTask):
    """
    Generic task for ritm manipulation (create/edit) in a table using a Glide form.
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
        pass

    def teardown(self) -> None:
        pass


class ChangeRitmStatusTask(ServiceNowRitmTask):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # get initial state of ritm
        self.initial_approval = self._get_initial_state()
    
    def all_configs(self):
        return json.load(open(CHANGE_RITM_STATUS_CONFIG_PATH))

    def _get_initial_state(self):
        ritm_number = self.config["ritm_number"]

        # get instance url and credentials
        instance_url = self.instance.snow_url
        snow_username, snow_password = self.instance.snow_credentials

        # Query sc_req_item to check the RITM status
        response = requests.get(
            f"{instance_url}/api/now/table/sc_req_item",
            auth=(snow_username, snow_password),
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={ritm_number}",
                "sysparm_fields": "sys_id,number,approval",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            raise ValueError(f"RITM {ritm_number} not found")
        return result[0]["approval"]

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        
        # get relevant info from config
        ritm_number = self.config["ritm_number"]
        approval = self.config["approval"]

        # get instance url and credentials
        instance_url = self.instance.snow_url
        snow_username, snow_password = self.instance.snow_credentials

        # Query sc_req_item to check the RITM status
        response = requests.get(
            f"{instance_url}/api/now/table/sc_req_item",
            auth=(snow_username, snow_password),
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={ritm_number}^approval={approval}",
                "sysparm_fields": "sys_id,number,approval",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if result:
            # Found a matching RITM with the correct status

            # TODO: revert state of RITM

            return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The requested item status was successfully updated."},
        )

        return (
                0,
                False,
                "",
                {"message": "The requested item status was not updated."},
            )

    def teardown(self) -> None:
        # revert to previous state
        if self.initial_approval and self.initial_approval != self.config["approval"]:
            try:
                requests.patch(
                    f"{self.instance.snow_url}/api/now/table/sc_req_item/{self.record_sys_id}",
                    auth=self.instance.snow_credentials,
                    headers={"Accept": "application/json"},
                    json={
                        "approval": self.initial_approval,
                    },
                )
            except HTTPError:
                # sys_id was stored in local storage (for submitted)
                # but the record is absent from the database (probably invalid form)
                pass            

class UpdateRitmQuantityTask(ServiceNowRitmTask):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # get initial quantity
        self.initial_quantity = self._get_initial_quantity()

    def all_configs(self):
        return json.load(open(UPDATE_RITM_QUANTITY_CONFIG_PATH))

    def _get_initial_quantity(self):
        ritm_number = self.config["ritm_number"]

        # Query sc_req_item to check the RITM status
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/sc_req_item",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={ritm_number}",
                "sysparm_fields": "sys_id,number,quantity",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            raise ValueError(f"RITM {ritm_number} not found")
        return result[0]["quantity"]


    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        # get relevant info from config
        ritm_number = self.config["ritm_number"]
        quantity = self.config["quantity"]

        # Query sn_customerservice_case in ServiceNow
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/sc_req_item",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={ritm_number}",
                "sysparm_fields": "sys_id,number,quantity",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])

        # check for quantity
        if result and int(result[0]["quantity"]) == int(quantity):
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "The ritm quantity was successfully updated."},
            )

        return (
                0,
                False,
                "",
                {"message": "The ritm quantity was not updated."},
            )


    def teardown(self) -> None:
        if self.initial_quantity and self.initial_quantity != self.config["quantity"]:
            try:
                requests.patch(
                    f"{self.instance.snow_url}/api/now/table/sc_req_item/{self.record_sys_id}",
                    auth=self.instance.snow_credentials,
                    headers={"Accept": "application/json"},
                    json={
                        "quantity": self.initial_quantity,
                    },
                )
            except HTTPError:
                # sys_id was stored in local storage (for submitted)
                # but the record is absent from the database (probably invalid form)
                pass
    
__TASKS__ = [
    ChangeRitmStatusTask,
    UpdateRitmQuantityTask,
]