import json

from playwright.sync_api._generated import Page

from .base import CompositionalTask, HumanEvalTask

from ..base import AbstractServiceNowTask
from ..form import CreateUserTask, CreateHardwareAssetTask
from ..knowledge import KnowledgeBaseSearchTask
from ..navigation import AllMenuTask
from ..service_catalog import OrderAppleMacBookPro15Task

from ...instance import SNowInstance
from ...config import CREATE_USER_CONFIG_PATH, CREATE_HARDWARE_CONFIG_PATH


class OnBoardUserTask(CompositionalTask, HumanEvalTask):
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
            A list of subtasks.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. e.g. "Referring to company protocol 'Onboarding a new user', onboard user with the following information: \n"
        short_description: str
            A short description of the task to be completed. e.g. "Onboard user John Doe"
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        self.protocol_name = "Onboarding a new user"
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            level=level,
            protocol_name=self.protocol_name,
        )

        self.all_user_configs = CreateUserTask.all_configs()
        self.all_hardware_asset_configs = CreateHardwareAssetTask.all_configs()
        self.task_description = None
        self.short_description = None

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        # Sample a configuration
        config = self.fixed_config if self.fixed_config else self._get_config()
        user_name = (
            config[3].fixed_config["template_record"]["first_name"]
            + " "
            + config[3].fixed_config["template_record"]["last_name"]
        )
        # Get the task description
        self.short_description = f"Onboard user {user_name}"
        self.task_description = f'Referring to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) onboard user with the following information: \n'

        goal, info = super().setup_goal(page=page, config=config)

        return goal, info

    def _get_config(self) -> list[AbstractServiceNowTask]:
        # Sample base configurations; the hardware config will be modified to include the assigned_to field
        user_config = self.random.choice(self.all_user_configs)
        hardware_config = self.random.choice(self.all_hardware_asset_configs)

        # Get the common fields between the user and hardware configurations to adjust the hardware config
        common_fields = [
            field for field in hardware_config["fields"].keys() if field in user_config["fields"]
        ]
        common_task_fields = [
            field for field in hardware_config["task_fields"] if field in user_config["task_fields"]
        ]
        common_template_record_fields = [
            field
            for field in hardware_config["template_record"].keys()
            if field in user_config["template_record"] and "sys" not in field
        ]

        # Drop the common fields as they create synchronization issues
        for field in common_fields + common_task_fields + common_template_record_fields:
            if field in user_config["fields"]:
                user_config["fields"].pop(field)
            if field in hardware_config["fields"]:
                hardware_config["fields"].pop(field)

            if field in user_config["task_fields"]:
                user_config["task_fields"].remove(field)
            if field in hardware_config["task_fields"]:
                hardware_config["task_fields"].remove(field)

            if field in user_config["template_record"]:
                user_config["template_record"].pop(field)
            if field in hardware_config["template_record"]:
                hardware_config["template_record"].pop(field)

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
                    "question": f"Can you find the '{self.protocol_name}' Protocol in the Knowledge Base?",
                    "value": "",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
        ]

        create_user_subtask = [
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
            CreateUserTask(
                instance=self.instance,
                fixed_config=user_config,
                is_validated=True,
                used_in_level_2=True,
            ),
        ]

        order_hardware_subtask = [
            # Navigate to the hardware asset list
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Self-Service",
                    "module": "Service Catalog",
                    "url": "/now/nav/ui/classic/params/target/catalog_home.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            # Order a MacBook Pro 15
            OrderAppleMacBookPro15Task(
                instance=self.instance,
                fixed_config={
                    "configuration": {},
                    "description": "Apple MacBook Pro",
                    "item": "Apple MacBook Pro 15",
                    "quantity": 1,
                },
                is_validated=True,
                used_in_level_2=True,
            ),
        ]
        # The unique name for the user is created once the task is instantiated
        user_full_name = (
            create_user_subtask[1].template_record["first_name"]
            + " "
            + create_user_subtask[1].template_record["last_name"]
        )
        # Set the assigned_to field in the hardware asset configuration to the user's email
        hardware_config["template_record"]["assigned_to"] = user_full_name
        if "assigned_to" not in hardware_config["task_fields"]:
            hardware_config["task_fields"].append("assigned_to")

        create_hardware_subtask = [
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
            # Create a new hardware asset
            CreateHardwareAssetTask(
                instance=self.instance,
                fixed_config=hardware_config,
                is_validated=True,
                used_in_level_2=True,
            ),
        ]

        config = (
            navigate_to_protocol_subtask
            + create_user_subtask
            + order_hardware_subtask
            + create_hardware_subtask
        )

        return config


__TASKS__ = [OnBoardUserTask]
