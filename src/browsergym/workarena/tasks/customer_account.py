import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api

from ..config import (
    FIND_CUSTOMER_ACCOUNT_MANAGER_CONFIG_PATH,
)
from .base import AbstractServiceNowTask


class ServiceNowCustomerAccountTask(AbstractServiceNowTask):


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


class FindCustomerAccountManagerTask(ServiceNowCustomerAccountTask):

    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        contact = self.config["contact"]

        if contact.lower() in chat_messages[-1]["message"].lower():
            return (
                1,
                True,
                "",
                {"message": "The customer account manager was successfully found."},
            )
        return (
            0,
            False,
            "",
            {"message": "The customer account manager was not found."},
        )

    def teardown(self) -> None:
        pass

    def all_configs(self):
        return json.load(open(FIND_CUSTOMER_ACCOUNT_MANAGER_CONFIG_PATH))

__TASKS__ = [
    FindCustomerAccountManagerTask,
]
