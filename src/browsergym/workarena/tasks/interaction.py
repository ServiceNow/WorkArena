import json
from typing import Any, Dict, List, Tuple

import playwright.sync_api
import requests

from ..api.utils import HTTPError, db_delete_from_table
from ..config import (
    CREATE_INTERACTION_CONFIG_PATH,
)
from .base import AbstractServiceNowTask


class ServiceNowInteractionTask(AbstractServiceNowTask):

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

class CreateInteractionTask(ServiceNowInteractionTask):
    
    def validate(self, page: playwright.sync_api.Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:

        # get customer problem from config
        customer_problem = self.config["customer_problem"]

        # Query interaction table using LIKE operator
        # TODO: difficult to verify and test
        # no way of guaranteeing correct retrieval based on short description
        # no existing interactions on the platform we can use to test function
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/interaction",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"short_descriptionLIKE{customer_problem}",
                "sysparm_fields": "sys_id,short_description",
                "sysparm_limit": 1,
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if result:
            # Interaction exists with matching short description
            # get sys_id from result
            sys_id = result[0]["sys_id"]
            self.created_sysids.append(sys_id)
            return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The interaction was successfully created."},
        )

        return (
                0,
                False,
                "",
                {"message": "The interaction was not found."},
            )


    def teardown(self) -> None:
        # go over all created sysids and delete that record in the interaction table
        for sys_id in self.created_sysids:
            if sys_id is not None:
                try:
                    db_delete_from_table(instance=self.instance, sys_id=sys_id, table="interaction")
                except HTTPError:
                    # sys_id was stored in local storage (for submitted)
                    # but the record is absent from the database (probably invalid form)
                    pass

    def all_configs(self):
        return json.load(open(CREATE_INTERACTION_CONFIG_PATH))
        