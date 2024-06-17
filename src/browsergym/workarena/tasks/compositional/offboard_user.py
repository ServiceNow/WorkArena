import json

from faker import Faker

fake = Faker()
from playwright.sync_api._generated import Page

from .base import CompositionalTask, HumanEvalTask
from .delete_record import DeleteUserTask

from ..base import AbstractServiceNowTask
from ..form import EditHardwareAssetTask
from ..knowledge import KnowledgeBaseSearchTask
from ..list import FilterHardwareListTask
from ..navigation import AllMenuTask

from ...api.computer_asset import create_computer_asset
from ...api.user import create_user
from ...api.utils import table_api_call, db_delete_from_table
from ...instance import SNowInstance


class OffBoardUserTask(CompositionalTask, HumanEvalTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Employee OffBoarding Task

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of subtasks.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. e.g. "Referring to company protocol 'Offboarding a user', offboard user XYZ"
        short_description: str
            A short description of the task to be completed. e.g. "Offboard user John Doe"
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        self.protocol_name = "Offboarding a user"
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            level=level,
            protocol_name=self.protocol_name,
        )
        self.task_description = None
        self.short_description = None
        self.user_full_name = None
        self.user_sys_id = None
        self.user_name = None
        self.laptop_asset_tag = None
        self.laptop_sys_id = None

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        # Generate random name for the user
        first_name = fake.first_name() + "-" + fake.first_name()
        last_name = fake.last_name() + "-" + fake.last_name()
        self.user_full_name = first_name + " " + last_name
        self.laptop_asset_tag = "P" + str(id(self) % (10**8)).zfill(8)

        # Create user
        self.user_name, _, self.user_sys_id = create_user(
            instance=self.instance, first_name=first_name, last_name=last_name, random=self.random
        )

        assert self.user_sys_id, f"Failed to create user {first_name} {last_name}"

        self.laptop_sys_id, _, _ = create_computer_asset(
            instance=self.instance,
            asset_tag=self.laptop_asset_tag,
            user_sys_id=self.user_sys_id,
            random=self.random,
        )

        config = self.fixed_config if self.fixed_config else self._get_config()
        # Get the task description
        self.short_description = f"Offboard user {self.user_full_name}"
        self.task_description = f'Referring to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) offboard user "{self.user_full_name}" \n'

        goal, info = super().setup_goal(page=page, config=config)

        return goal, info

    def _get_config(self) -> list[AbstractServiceNowTask]:
        """Sample a user configuration and a hardware asset configuration. Add the assigned_to field if missing
        from the hardware asset configuration. Finally, return the list of subtasks, with navigation subtasks included.
        """
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
        unassign_hardware_subtask = [
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
            # Create a new hardware asset
            EditHardwareAssetTask(
                instance=self.instance,
                record_sys_id=self.laptop_sys_id,
                new_values={"assigned_to": ""},
                is_validated=True,
                used_in_level_2=True,
                level=self.level,
            ),
        ]
        delete_user_subtask = [
            # Navigate to the user list
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "System Security",
                    "module": "Users and Groups > Users",
                    "url": "/now/nav/ui/classic/params/target/sys_user_list.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            # Create a new user
            DeleteUserTask(
                instance=self.instance,
                fixed_config={
                    "field_name": "name",
                    "pretty_printed_field_name": "Name",
                    "field_value": self.user_full_name,
                    "other_fields": {},
                },
                record_sys_id=self.user_sys_id,
                is_validated=True,
                used_in_level_2=True,
            ),
        ]

        config = navigate_to_protocol_subtask + unassign_hardware_subtask + delete_user_subtask

        return config

    def teardown(self) -> None:
        # Delete the user
        user_record = table_api_call(
            instance=self.instance,
            table="sys_user",
            params={"sysparm_query": f"sys_id={self.user_sys_id}"},
        )["result"]
        if user_record:
            db_delete_from_table(
                instance=self.instance,
                table="sys_user",
                sys_id=self.user_sys_id,
            )
        super().teardown()


__TASKS__ = [OffBoardUserTask]
