import os
import requests
import re

from typing import Optional

from .config import SNOW_BROWSER_TIMEOUT


class SNowInstance:
    """
    Utility class to access a ServiceNow instance.

    """

    def __init__(
        self,
        snow_url: Optional[str] = None,
        snow_credentials: Optional[tuple[str, str]] = None,
    ) -> None:
        """
        Set up a ServiceNow instance API

        Parameters:
        -----------
        snow_url: str
            The URL of a SNow instance. If None, will try to get the value from the environment variable SNOW_INSTANCE_URL.
        snow_credentials: (str, str)
            The username and password used to access the SNow instance. If None, will try to get the values from the
            environment variables SNOW_INSTANCE_UNAME and SNOW_INSTANCE_PWD.

        """
        # try to get these values from environment variables if not provided
        if snow_url is None:
            if "SNOW_INSTANCE_URL" in os.environ:
                snow_url = os.environ["SNOW_INSTANCE_URL"]
            else:
                raise ValueError(
                    f"Please provide a ServiceNow instance URL (you can use the environment variable SNOW_INSTANCE_URL)"
                )

        if snow_credentials is None:
            if "SNOW_INSTANCE_UNAME" in os.environ and "SNOW_INSTANCE_PWD" in os.environ:
                snow_credentials = (
                    os.environ["SNOW_INSTANCE_UNAME"],
                    os.environ["SNOW_INSTANCE_PWD"],
                )
            else:
                raise ValueError(
                    f"Please provide ServiceNow credentials (you can use the environment variables SNOW_INSTANCE_UNAME and SNOW_INSTANCE_PWD)"
                )

        # remove trailing slashes in the URL, if any
        self.snow_url = snow_url.rstrip("/")
        self.snow_credentials = snow_credentials
        self.check_status()

    def check_status(self):
        """
        Check the status of the ServiceNow instance. Raises an error if the instance is not ready to be used.

        """
        self._check_is_reachable()
        self._check_is_hibernating()

    def _check_is_hibernating(self):
        """
        Test that the ServiceNow instance is not hibernating

        """
        response = requests.get(self.snow_url, timeout=SNOW_BROWSER_TIMEOUT)

        # Check if the response contains any indication of the instance being in hibernation
        if "hibernating" in response.text.lower():
            raise RuntimeError(
                f"ServiceNow instance is hibernating. Please navigate to {self.snow_url} wake it up."
            )

    def _check_is_reachable(self):
        """
        Test that the ServiceNow instance is reachable

        """
        try:
            requests.get(self.snow_url, timeout=SNOW_BROWSER_TIMEOUT)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise RuntimeError(
                f"ServiceNow instance at {self.snow_url} is not reachable. Please check the URL."
            )
