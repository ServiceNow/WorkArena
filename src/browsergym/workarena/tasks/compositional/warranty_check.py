import json
import time
from faker import Faker

fake = Faker()

from playwright.sync_api._generated import Page

from .base import CompositionalTask, HumanEvalTask

from ..base import AbstractServiceNowTask
from ..knowledge import KnowledgeBaseSearchTask
from ..list import ExtractListInfoTask, FilterHardwareListTask
from ..navigation import AllMenuTask

from ...api.computer_asset import create_computer_asset
from ...api.user import create_user
from ...api.utils import db_delete_from_table, table_api_call
from ...instance import SNowInstance


class GetWarrantyExpirationDateTask(CompositionalTask, HumanEvalTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Create a compositional task with specific subtasks

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of subtasks
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. e.g. "Referring to company protocol '[company_protocol]', onboard user with the following information: \n"
        short_description: str
            A short description of the task to be completed. e.g. "Find the warranty expiration date for John Doe's laptop"
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        self.protocol_name = "Finding the warranty expiration for a user's laptop"
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            level=level,
            protocol_name=self.protocol_name,
        )
        self.task_description = None
        self.short_description = None
        self.user_sys_id = None
        self.user_name = None
        self.user_full_name = None
        self.laptop_sys_id = None
        self.warranty_expiration_date = None

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        # Create a user and a laptop for the user
        self._create_user_and_laptop()

        # Sample a configuration
        config = self.fixed_config if self.fixed_config else self._get_config()

        # Get the task description
        self.short_description = (
            f"Find the warranty expiration date for {self.user_full_name}'s laptop"
        )
        self.task_description = f'Refer to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) for the steps to find the Warranty expiration date for {self.user_full_name}\'s laptop.\n \n'

        goal, info = super().setup_goal(page=page, config=config)

        return goal, info

    def _get_config(self) -> list[AbstractServiceNowTask]:
        navigate_to_protocol_subtask = [
            # Navigate to the KB
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Self-Service",
                    "module": "Knowledge",
                    "url": "/now/nav/ui/classic/params/target/%24knowledge.do",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
            # Find the protocol for on-boarding a new user
            KnowledgeBaseSearchTask(
                instance=self.instance,
                fixed_config={
                    "alternative_answers": [],
                    "item": f"{self.protocol_name}",
                    "question": f'Can you find the "{self.protocol_name}" Protocol in the Knowledge Base?',
                    "value": "",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
        ]
        navigate_to_hardware_asset_and_filter = [
            # Navigate to the hardware asset list
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Asset",
                    "module": "Portfolios > Hardware Assets",
                    "url": "/now/nav/ui/classic/params/target/alm_hardware_list.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            # Filter the hardware asset list
            FilterHardwareListTask(
                instance=self.instance,
                fixed_config={
                    "filter_columns": ["assigned_to"],
                    "filter_kind": "AND",
                    "filter_values": [f"{self.user_full_name}"],
                },
                is_validated=False,
                used_in_level_2=True,
            ),
        ]
        extract_warranty_subtask = [
            ExtractListInfoTask(
                instance=self.instance,
                unique_field_name="assigned_to",
                fixed_config={
                    "start_rel_url": "",
                    "fields": {
                        "assigned_to": "Assigned to",
                        "warranty_expiration": "Warranty expiration",
                    },
                    "expected_values": [
                        {
                            "assigned_to": f"{self.user_full_name}",
                            "warranty_expiration": f"{self.warranty_expiration_date}",
                        }
                    ],
                },
                list_name="Hardware Assets",
                list_url="/now/nav/ui/classic/params/target/alm_hardware_list.do",
                table_name="alm_hardware",
                is_validated=True,
                used_in_level_2=True,
            ),
        ]

        config = (
            navigate_to_protocol_subtask
            + navigate_to_hardware_asset_and_filter
            + extract_warranty_subtask
        )

        return config

    def _create_user_and_laptop(self) -> None:
        """
        Creates a user and a laptop for the user. The laptop model is randomly selected from the available computer models.
        Sets the user_sys_id, laptop_sys_id, user_name and warranty_expiration_date attributes.
        """
        # Generate random name for the user
        first_name = fake.first_name() + "-" + fake.first_name()
        last_name = fake.last_name() + "-" + fake.last_name()
        self.user_full_name = first_name + " " + last_name
        # Create user
        self.user_name, _, self.user_sys_id = create_user(
            instance=self.instance, first_name=first_name, last_name=last_name, random=self.random
        )

        assert self.user_sys_id, f"Failed to create user {first_name} {last_name}"
        self.warranty_expiration_date = str(fake.date_between(start_date="-1y", end_date="+1y"))
        asset_tag = "P" + str(id(self) % (10**8)).zfill(8)
        (
            computer_sys_id,
            _,
            _,
        ) = create_computer_asset(
            instance=self.instance,
            asset_tag=asset_tag,
            warranty_expiration_date=self.warranty_expiration_date,
            user_sys_id=self.user_sys_id,
            random=self.random,
        )

        assert computer_sys_id, f"Failed to create hardware asset {asset_tag}"
        self.laptop_sys_id = computer_sys_id

    def teardown(self) -> None:
        # Delete the user and the laptop
        user_record_exists = table_api_call(
            instance=self.instance,
            table="sys_user",
            params={"sysparm_query": f"sys_id={self.user_sys_id}"},
        )
        laptop_record_exists = table_api_call(
            instance=self.instance,
            table="alm_hardware",
            params={"sysparm_query": f"sys_id={self.laptop_sys_id}"},
        )
        if user_record_exists:
            db_delete_from_table(
                instance=self.instance,
                table="sys_user",
                sys_id=self.user_sys_id,
            )
        if laptop_record_exists:
            db_delete_from_table(
                instance=self.instance,
                table="alm_hardware",
                sys_id=self.laptop_sys_id,
            )
        super().teardown()


__TASKS__ = [GetWarrantyExpirationDateTask]
