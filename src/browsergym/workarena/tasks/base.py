"""
A bunch of base classes

"""

import logging

import numpy as np
import playwright.sync_api

from typing import Optional, List, Tuple
from uuid import uuid4
from urllib.parse import urlparse

from browsergym.core.task import AbstractBrowserTask
from ..config import SNOW_BROWSER_TIMEOUT, SNOW_JS_UTILS_FILEPATH
from ..utils import impersonate_user, ui_login
from ..instance import SNowInstance


class AbstractServiceNowTask(AbstractBrowserTask):
    """
    A base class for tasks that interacts with the ServiceNow instance

    """

    def __init__(
        self,
        start_rel_url: str,
        instance: SNowInstance = None,
        final_rel_url: Optional[str] = None,
        username: Optional[str] = "admin",
    ) -> None:
        """
        Initialize the task

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance in which the task will be performed
        start_url: str
            The URL for the starting page of the task
        final_url: str (optional)
            The URL for the final page of the task (default: uses the value of base_url)
        username: str (optional)
            The username of the user to impersonate to run the task (default: admin)

        """
        self.instance = instance if instance is not None else SNowInstance()
        self.start_url = self.instance.snow_url + start_rel_url
        self.username = username

        if final_rel_url is not None:
            self.final_url = self.instance.snow_url + final_rel_url
        else:
            self.final_url = self.start_url
        self.final_url_ = urlparse(self.final_url)

    def _add_init_scripts_to_context_and_reload(
        self, page: playwright.sync_api.Page, scripts: List[str]
    ) -> None:
        for script in scripts:
            page.context.add_init_script(script)
        page.reload()

    def cheat(self, page: playwright.sync_api.Page, chat_messages: list[str]) -> None:
        # Don't call super cheat function because it's not implemented at the base level
        logging.debug("Cheat is solving the task")

    @classmethod
    def get_task_id(cls):
        # Get the class name and remove the word 'Task' from the end if it exists
        class_name = cls.__name__.replace("Task", "")
        # Convert CamelCase to hyphen-separated format
        formatted_name = "".join(
            ["-" + i.lower() if i.isupper() else i for i in class_name]
        ).lstrip("-")
        return f"workarena.servicenow.{formatted_name}"

    def pre_setup(self, seed: int, page: playwright.sync_api.Page):
        logging.debug("Setting up base task")

        # Set the page timeout
        page.set_default_timeout(SNOW_BROWSER_TIMEOUT)

        # Load a few utility functions for init scripts
        page.add_init_script(path=SNOW_JS_UTILS_FILEPATH)

        # Set the task's unique ID
        self.unique_id = str(uuid4())
        self.random = np.random.RandomState(seed)
        self.page = page  # Keep the page for client-side validation

        # Authenticate
        ui_login(
            instance=self.instance,
            page=page,
        )

        # Impersonate if needed
        if self.username != "admin":
            impersonate_user(self.username, page)

        # Navigate to the task's url
        page.goto(self.start_url)

    def teardown(self) -> None:
        logging.debug("Tearing down the task")
