import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api

from ..config import (
    GET_NUMBER_LICENSES_CONFIG_PATH,
)
from .base import AbstractServiceNowTask


class ServiceNowLicenseTask(AbstractServiceNowTask):

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


class GetNumberLicensesTask(ServiceNowLicenseTask):

    def all_configs(self):
        return json.load(open(GET_NUMBER_LICENSES_CONFIG_PATH))
    
    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        num_licenses = self.config["number_of_licenses"]

        if str(num_licenses) in chat_messages[-1]["message"].lower():
            return (1, True, "Nice work, thank you!", {"message": "The number of licenses was successfully retrieved."})
        return (0, False, "", {"message": "The number of licenses was not retrieved."})

    def teardown(self) -> None:
        pass