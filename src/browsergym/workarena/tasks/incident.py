import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

from ..api.utils import HTTPError, db_delete_from_table, table_api_call
from ..config import (
    ADD_ADDITIONAL_ASSIGNEE_TO_INCIDENT_CONFIG_PATH,
    UPDATE_INCIDENT_CONFIG_PATH,
    RESOLVE_INCIDENT_CONFIG_PATH,
)
from .base import AbstractServiceNowTask


class ServiceNowIncidentTask(AbstractServiceNowTask):

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

class CreateIncidentTask(ServiceNowIncidentTask):
    pass

class CreateChildIncidentTask(ServiceNowIncidentTask):
    pass

class CreateIncidentWithWatchlistTask(ServiceNowIncidentTask):
    pass


class AddAdditionalAssigneeToIncidentTask(ServiceNowIncidentTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_incident_additional_assignee_list = self._get_initial_incident_additional_assignee_list()

    def _get_initial_incident_additional_assignee_list(self):
        incident_number = self.config["incident_number"]

        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/incident",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={incident_number}",
                "sysparm_fields": "sys_id,additional_assignee_list",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            raise ValueError(f"Incident {incident_number} not found")

        return result[0]["additional_assignee_list"]

    def all_configs(self):
        return json.load(open(ADD_ADDITIONAL_ASSIGNEE_TO_INCIDENT_CONFIG_PATH))

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        incident_number = self.config["incident_number"]
        additional_assignee_list = self.config["additional_assignee_list"]

        # Query incident table in ServiceNow
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/incident",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={incident_number}",
                "sysparm_fields": "sys_id,number,additional_assignee_list",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])

        # check for additional_assignee_list
        if result and result[0]["additional_assignee_list"] == additional_assignee_list:
            # TODO: validate whether the verification is OK
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "The additional assignee was added to the incident."},
            )
        return (
            0,
            False,
            "",
            {"message": "The additional assignee was not added to the incident."},
        )

    def teardown(self):
        # revert the additional_assignee_list to the initial value
        if self.initial_incident_additional_assignee_list is not None and self.config["additional_assignee_list"] != self.initial_incident_additional_assignee_list:
            try:
                requests.patch(
                    f"{self.instance.snow_url}/api/now/table/incident/{self.config['incident_number']}",
                    auth=self.instance.snow_credentials,
                    headers={"Accept": "application/json"},
                    json={
                        "additional_assignee_list": self.initial_incident_additional_assignee_list,
                    },
                )
            except HTTPError:
                pass



class UpdateIncidentTask(ServiceNowIncidentTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_incident_urgency = self._get_initial_incident_urgency()
        self.comment_sys_id = None
    
    def _get_initial_incident_urgency(self):
        incident_number = self.config["incident_number"]

        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/incident",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={incident_number}",
                "sysparm_fields": "sys_id,urgency",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            raise ValueError(f"Incident {incident_number} not found")

        return result[0]["urgency"]

    def all_configs(self):
        return json.load(open(UPDATE_INCIDENT_CONFIG_PATH))

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        incident_number = self.config["incident_number"]
        comment = self.config["comment"]
        updated_urgency = self.config["updated_urgency"]

        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/incident",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={incident_number}",
                "sysparm_fields": "sys_id,urgency",
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
                {"message": "The incident was not found."},
            )

        if int(result[0]["urgency"]) != int(updated_urgency):
            return (
                0,
                False,
                "",
                {"message": "The urgency was not updated."},
            )

        incident_sys_id = result[0]["sys_id"]

        # search for comments in sys_journal_field
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/sys_journal_field",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"element_id={incident_sys_id}",
                "sysparm_fields": "sys_id,value",
                "sysparm_limit": 100,
            },
        )
        response.raise_for_status()

        result = response.json().get("result", [])
        if not result:
            return (
                0,
                False,
                "",
                {"message": "The comment was not found."},
            )

        for entry in result:
            if entry["value"].lower() == comment.lower():
                self.comment_sys_id = entry["sys_id"]
                return (
                    1,
                    True,
                    "Nice work, thank you!",
                    {"message": "The comment was found."},
                )
        return (
            0,
            False,
            "",
            {"message": "The comment was not found."},
        )

    def teardown(self):
        # revert the urgency to the initial value
        if self.initial_incident_urgency is not None and self.config["updated_urgency"] != self.initial_incident_urgency:
            try:
                table_api_call(
                    instance=self.instance,
                    table="incident",
                    params={
                        "sysparm_query": f"number={self.config['incident_number']}",
                    },
                    data={
                        "urgency": self.initial_incident_urgency,
                        "comments": "", # empty comments
                    },
                    method="PUT",
                )
            except HTTPError:
                pass

        # remove the comment
        if self.comment_sys_id is not None:
            try:
                db_delete_from_table(
                    instance=self.instance,
                    table="sys_journal_field",
                    sys_id=self.comment_sys_id,
                )
            except HTTPError:
                pass


class ResolveIncidentTask(ServiceNowIncidentTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._get_initial_incident_info()
    
    def _get_initial_incident_info(self):
        
        incident_number = self.config["incident_number"]

        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/incident",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={incident_number}",
                "sysparm_fields": "sys_id,number,close_code,close_notes,state",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            raise ValueError(f"Incident {incident_number} not found")

        self.incident_sys_id = result[0]["sys_id"]
        self.initial_incident_state = result[0]["state"]
        self.initial_incident_close_code = result[0]["close_code"]        
    
    def all_configs(self):
        return json.load(open(RESOLVE_INCIDENT_CONFIG_PATH))

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        incident_number = self.config["incident_number"]

        # Query sc_req_item to check the RITM status
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/incident",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"number={incident_number}",
                "sysparm_fields": "sys_id,number,close_code,close_notes",
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
                {"message": "The incident was not found."},
            )


        # check if the close code is ok
        if result[0]["close_code"] != self.config["close_code"]:
            return (
                0,
                False,
                "",
                {"message": "The close code is not correct."},
            )

        # check if the close notes is ok
        if result[0]["close_notes"] != self.config["close_notes"]:
            return (
                0,
                False,
                "",
                {"message": "The close notes are not correct."},
            )

        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The incident was successfully resolved."},
        )

    def teardown(self) -> None:
        # reset the close code to the initial value
        if self.initial_incident_close_code is not None and self.config["close_code"] != self.initial_incident_close_code:
            try:
                requests.patch(
                    f"{self.instance.snow_url}/api/now/table/incident/{self.incident_sys_id}",
                    auth=self.instance.snow_credentials,
                    headers={"Accept": "application/json"},
                    json={
                        "close_code": self.initial_incident_close_code,
                        "close_notes": "",
                        "state": self.initial_incident_state,
                    },
                )
            except HTTPError:
                # sys_id was stored in local storage (for submitted)
                # but the record is absent from the database (probably invalid form)
                pass


class CreateIncidentTasksTask(ServiceNowIncidentTask):
    pass

__TASKS__ = [
    ResolveIncidentTask,
    AddAdditionalAssigneeToIncidentTask,
]