from faker import Faker

fake = Faker()

from playwright.sync_api._generated import Page

from browsergym.workarena.tasks.knowledge import KnowledgeBaseSearchTask
from browsergym.workarena.tasks.list import FilterListTask
from browsergym.workarena.tasks.navigation import AllMenuTask

from .base import CompositionalTask

from ..base import AbstractServiceNowTask

from ...instance import SNowInstance


class FilterAndDoTask(CompositionalTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        navigation_config: dict = None,
        protocol_name: str = None,
        level: int = 2,
    ) -> None:
        """
        Generic task to navigate to a specific page, run a filter and perform a task.

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of tuples, each containing a subtask
        navigation_config: dict
            Configuration to use for the navigation to the list that will be filtered. Contains application and module.
            URL is not necessary as the navigation steps are not validated
        protocol_name: str
            The name of the protocol to refer to in the task description for L3.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.

        Attributes:
        -----------
        filter_config: dict
            Configuration to use for the filter that will be applied to the list. Contains filter_columns, filter_values and filter_kind in addition to the path to the expected fields in the list.
            this is set by the _setup_list method.
        tasks: List[AbstractServiceNowTask]
            The tasks to perform after having filtered the list. Set by the child setup
        task_description: str
            The start of the task description to be completed. Provided by the child class.
        short_description: str
            A short description of the task to be completed. "Create a new user". Provided by the child class.
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            level=level,
        )
        self.used_in_level_2 = self.level == 2
        self.navigation_config = navigation_config
        self.filter_config = None
        self.protocol_name = protocol_name
        self.task_description = None
        self.short_description = None
        self.tasks = []

    def _setup_list(self) -> None:
        """Used to create the necessary records in the list + setting up the list filter attribute before filtering it."""
        raise NotImplementedError

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self._setup_list()
        config = self.fixed_config if self.fixed_config else self._get_config()

        goal, info = super().setup_goal(page=page, config=config)

        return goal, info

    def _get_config(self) -> list[AbstractServiceNowTask]:
        list_url = self.filter_config["list_url"]

        navigate_to_protocol_config = [
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

        config = [
            # Navigate to the task start page
            AllMenuTask(
                instance=self.instance,
                fixed_config=self.navigation_config,
                is_validated=False,
                used_in_level_2=True,
            ),
            # Filter the the list; the config it uses is set by the _setup_list method
            FilterListTask(
                instance=self.instance,
                list_url=list_url,
                fixed_config=self.filter_config,
                expected_fields_path=self.filter_config["expected_fields_path"],
                is_validated=False,
                used_in_level_2=True,
            ),
        ] + self.tasks

        # To support the option of having no protocol
        if self.protocol_name:
            config = navigate_to_protocol_config + config

        return config
