"""
A bunch of base classes

"""

import logging

import numpy as np
import playwright.sync_api

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from urllib import parse

from browsergym.core.task import AbstractBrowserTask
from ..api.user import create_user
from ..api.utils import table_api_call
from ..config import SNOW_BROWSER_TIMEOUT, SNOW_JS_UTILS_FILEPATH
from ..utils import impersonate_user, url_login
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
        username: Optional[str] = "admin",
    ) -> None:
        """
        Initialize the task

        Parameters:
        -----------
        seed: int
            Random seed
        instance: SNowInstance
            The ServiceNow instance in which the task will be performed
        start_url: str
            The URL for the starting page of the task
        final_url: str (optional)
            The URL for the final page of the task (default: uses the value of base_url)

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

        # Keep the page for client-side validation
        self.page = page

        # Set the page timeout
        page.set_default_timeout(SNOW_BROWSER_TIMEOUT)

        # Set the task's unique ID
        self.unique_id = str(uuid4())

        # Configure the task
        goal, info = self.setup_goal(page=page)

        # Load a few utility functions for init scripts
        page.add_init_script(path=SNOW_JS_UTILS_FILEPATH)

        # Add the initialization scripts to the page context
        for script in self.get_init_scripts():
            page.context.add_init_script(script)

        # Create a new user to run the task
        self._base_initial_instance = self.instance
        self._base_user_name, self._base_user_password, self._base_user_sysid = create_user(
            self.instance
        )
        self.instance = deepcopy(self.instance)
        self.instance.snow_credentials = (self._base_user_name, self._base_user_password)

        # Start the task if requested
        if do_start:
            self.start(page)

        return goal, info

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
        logging.debug("Tearing down the task")

        # Delete the user
        table_api_call(
            instance=self._base_initial_instance,
            table=f"sys_user/{self._base_user_sysid}",
            method="DELETE",
        )
