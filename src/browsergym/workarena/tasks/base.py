"""
A bunch of base classes

"""

import logging

import numpy as np
import playwright.sync_api

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import List, Optional, Tuple
from uuid import uuid4
from urllib import parse

from browsergym.core.task import AbstractBrowserTask
from ..api.user import create_user
from ..api.utils import table_api_call
from ..config import SNOW_BROWSER_TIMEOUT, SNOW_JS_UTILS_FILEPATH
from ..utils import url_login
from ..instance import SNowInstance


class AbstractServiceNowTask(AbstractBrowserTask, ABC):
    """
    A base class for tasks that interacts with the ServiceNow instance

    """

    def __init__(
        self,
        seed: int,
        start_rel_url: str,
        instance: SNowInstance = None,
        final_rel_url: Optional[str] = None,
        user_roles: List[str] = ["admin"],
        has_description: bool = False,
    ) -> None:
        """
        Initialize the task

        Parameters:
        -----------
        seed: int
            Random seed
        instance: SNowInstance
            The ServiceNow instance in which the task will be performed
        start_rel_url: str
            The URL for the starting page of the task
        final_rel_url: str (optional)
            The URL for the final page of the task (default: uses the value of base_url)
        user_roles: list[str]
            The roles to assign to the user (default: ["admin"])
        has_description: bool
            Whether the task has a description in L3 compositional tasks

        """
        super().__init__(seed)

        # task properties, will be used to set up the browsergym environment
        self.viewport = {"width": 1280, "height": 720}
        self.slow_mo = 1000  # ms
        self.timeout = 10000  # ms

        self.instance = instance if instance is not None else SNowInstance()
        self.start_url = self.instance.snow_url + start_rel_url

        if final_rel_url is not None:
            self.final_url = self.instance.snow_url + final_rel_url
        else:
            self.final_url = self.start_url
        self.final_url_ = parse.urlparse(self.final_url)

        # Set the task's unique ID
        self.unique_id = str(uuid4())
        # Flag to ensure the task is setup only once
        self.task_is_setup = False
        self.delete_user_on_teardown = False
        self.user_roles = user_roles
        self.has_description = (
            has_description  # Whether the task has a description in L3 compositional tasks
        )

    def cheat(self, page: playwright.sync_api.Page, chat_messages: list[str]) -> None:
        # Don't call super cheat function because it's not implemented at the base level
        logging.debug("Cheat is solving the task")

    def get_init_scripts(self) -> List[str]:
        """
        Get the initialization scripts for the task. These are javascript scripts that will be run
        on any page and iframe that is loaded during the task.

        """
        return []

    @classmethod
    def get_task_id(cls):
        # Get the class name and remove the word 'Task' from the end if it exists
        class_name = cls.__name__.replace("Task", "")
        # Convert CamelCase to hyphen-separated format
        formatted_name = "".join(
            ["-" + i.lower() if i.isupper() else i for i in class_name]
        ).lstrip("-")
        return f"workarena.servicenow.{formatted_name}"

    def setup(self, page: playwright.sync_api.Page, do_start=True) -> tuple[str, dict]:
        """
        Set up the task

        Parameters:
        -----------
        page: playwright.sync_api.Page
            The Playwright page object
        do_start: bool
            Whether to start the task or not (including navigating to start page) (default: True)

        """
        logging.debug("Setting up the base task")
        if self.task_is_setup:
            raise ValueError("The task is already setup")

        # Keep the page for client-side validation
        self.page = page

        # Set the page timeout
        page.set_default_timeout(SNOW_BROWSER_TIMEOUT)

        # Create a new user to run the task if this is the starting task
        if do_start:
            self._base_initial_instance = self.instance
            self._base_user_name, self._base_user_password, self._base_user_sysid = create_user(
                instance=self.instance, user_roles=self.user_roles, random=self.random
            )
            self.instance = deepcopy(self.instance)
            self.instance.snow_credentials = (self._base_user_name, self._base_user_password)
            self.delete_user_on_teardown = True
        # Set the task's unique ID
        self.unique_id = str(uuid4())

        # Configure the task
        goal, info = self.setup_goal(page=page)

        # Load a few utility functions for init scripts
        page.context.add_init_script(path=SNOW_JS_UTILS_FILEPATH)

        # Add the initialization scripts to the page context
        for script in self.get_init_scripts():
            page.context.add_init_script(script)

        # Start the task if requested
        if do_start:
            self.start(page)

        self.task_is_setup = True

        return goal, info

    def create_user(self, first_name: str = None, last_name: str = None):
        """
        Create a user in the ServiceNow instance

        """

    @abstractmethod
    def setup_goal(self, page: playwright.sync_api.Page) -> tuple[str, dict]:
        """
        Setup the task configuration and produce the goal

        """
        pass

    def start(self, page: playwright.sync_api.Page) -> None:
        logging.debug("Navigating to task start page")

        # Authenticate
        url_login(
            instance=self.instance,
            page=page,
        )

        # Navigate to the task's url
        page.goto(self.start_url)

    def teardown(self) -> None:
        """
        Clean up after the task

        Notes:
        ------
        This method should not make assumptions on the state of the page (e.g., a specific URL).

        """
        logging.debug("Tearing down the task")

        if self.delete_user_on_teardown:
            # Delete the user
            table_api_call(
                instance=self._base_initial_instance,
                table=f"sys_user/{self._base_user_sysid}",
                method="DELETE",
            )
