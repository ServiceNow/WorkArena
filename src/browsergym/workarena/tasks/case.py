from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

from ..api.utils import (
    HTTPError,
    db_delete_from_table,
    table_api_call,
    table_column_info,
)
from .base import AbstractServiceNowTask

class ServiceNowCaseTask(AbstractServiceNowTask):
    

    def __init__(self, seed: int, config: Dict[str, Any]) -> None:
        super().__init__(seed)
        self.task_is_setup = False
        self.config = config
        self.timeout = 60000

    def setup_goal(self, page: playwright.sync_api.Page) -> Tuple[str, dict]:
        goal = self.config["goal"]
        info = self.config
        return goal, info


class GetCaseStatusTask(ServiceNowCaseTask):

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        state = self.config["state"]
        if state.lower() in chat_messages[-1]["content"].lower():
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "The state does match."},
            )
        return (
            0,
            False,
            "",
            {"message": "The state does not match."},
        )


class CloseCaseTask(ServiceNowCaseTask):
    
    def __init__(self, seed: int, config: Dict[str, Any]) -> None:
        super().__init__(seed, config)

        self.initial_state = table_api_call(
            instance=self.instance,
            table="sn_customerservice_case",
            params={
                "sysparm_query": f"number={self.config['case_number']}",
                "sysparm_fields": "state",
                "sysparm_limit": 1,
            },
        )["result"][0]["state"]

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        
        # gather info from config
        case_number = self.config["case_number"]
        resolution_code = self.config["resolution_code"]
        close_notes = self.config["close_notes"]
        
        # Query sn_customerservice_case in ServiceNow
        record = table_api_call(
            instance=self.instance,
            table="sn_customerservice_case",
            params={
                "sysparm_query": f"number={case_number}",
                "sysparm_fields": "sys_id,number,resolution_code,close_notes",
                "sysparm_limit": 1,
            },
        )["result"]

        if not record:
            return (
                0,
                False,
                "",
                {"message": "The record was not found in the database. Perhaps it was deleted."},
            )

        # check for resolution_code and close_notes
        if record[0]["resolution_code"] == resolution_code and record[0]["close_notes"] == close_notes:
            # TODO: allow fuzzy match for close_notes
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "The record was successfully edited."},
            )
        return (
            0,
            False,
            "",
            {"message": "The resolution code or close notes do not match."},
        )

    def teardown(self) -> None:
        
        # revert the state to initial_state
        table_api_call(
            instance=self.instance,
            table="sn_customerservice_case",
            method="POST",
            data={
                "state": self.initial_state,
            },
            params={
                "sysparm_query": f"number={self.config['case_number']}",
                "sysparm_fields": "state",
                "sysparm_limit": 1,
            },
        )


class GetCaseResolutionNotesTask(ServiceNowCaseTask):
    
    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        close_notes = self.config["close_notes"]

        # check for close_notes
        if close_notes.lower() in chat_messages[-1]["content"].lower():
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "The record was successfully edited."},
            )
        return (
            0,
            False,
            "",
            {"message": "The close notes do not match."},
        )    

class FindAssetUnderAccountCreateCaseTask(ServiceNowCaseTask):
    
    def __init__(self, seed: int, config: Dict[str, Any]) -> None:
        super().__init__(seed, config)
        self.record_sys_id = None

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        customer_account = self.config["customer_account"]    
        assets = [elem.strip() for elem in self.config.get("assets", "").split(",")]

        # find customer account sys id
        result = table_api_call(
            instance=self.instance,
            table="customer_account",
            params={
                "sysparm_query": f"nameSTARTSWITH{customer_account}",
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
                {"message": "The customer account was not found."},
            )
        account_sys_id = result[0]["sys_id"]

        # Query sn_customerservice_case in ServiceNow
        result = table_api_call(
            instance=self.instance,
            table="sn_customerservice_case",
            params={
                "sysparm_query": f"account={account_sys_id}",
                "sysparm_fields": "sys_id,short_description",
                "sysparm_display_value": "true",
            },
        )["result"]

        if not result:
            return (
                0,
                False,
                "",
                {"message": "The case was not found."},
            )

        self.record_sys_id = result[0]["sys_id"]
        short_descriptions = [case["short_description"] for case in result]

        # check for assets
        # TODO: this is not the best way to do it
        for short_description in short_descriptions:
            print(short_description)
            if all(asset.lower() in short_description.lower() for asset in assets):
                return (
                    1,
                    True,
                    "Nice work, thank you!",
                    {"message": "The record was successfully edited."},
                )
        return (
            0,
            False,
            "",
            {"message": "The assets do not match."},
        )

    def teardown(self) -> None:
        # TODO: is this robust enough?
        if self.record_sys_id is not None:
            db_delete_from_table(
                instance=self.instance,
                sys_id=self.record_sys_id,
                table="sn_customerservice_case",
            )
