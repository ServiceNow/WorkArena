import os
import requests
import re
from playwright.sync_api import sync_playwright
from typing import Optional
from requests.exceptions import HTTPError
from time import sleep

from .config import SNOW_BROWSER_TIMEOUT

# ServiceNow API configuration
SNOW_API_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


class SNowInstance:
    """
    Utility class to access a ServiceNow instance.

    """

    def __init__(
        self,
        snow_url: Optional[str] = None,
        snow_credentials: Optional[tuple[str, str]] = None,
        check_installed: bool = True,
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
        if check_installed:
            self.check_is_installed()

    def table_api_call(
        self,
        table: str,
        data: dict = {},
        params: dict = {},
        json: dict = {},
        method: str = "GET",
        wait_for_record: bool = False,
        max_retries: int = 5,
        raise_on_wait_expired: bool = True,
    ) -> dict:
        """
        Make a call to the ServiceNow Table API
        """
        # Query API
        response = requests.request(
            method=method,
            url=self.snow_url + f"/api/now/table/{table}",
            auth=self.snow_credentials,
            headers=SNOW_API_HEADERS,
            data=data,
            params=params,
            json=json,
        )
        if method == "POST":
            sys_id = response.json()["result"]["sys_id"]
            data = {}
            params = {"sysparm_query": f"sys_id={sys_id}"}

        # Check for HTTP success code (fail otherwise)
        response.raise_for_status()

        record_exists = False
        num_retries = 0
        if method == "POST" or wait_for_record:
            while not record_exists:
                sleep(0.5)
                get_response = self.table_api_call(
                    table=table,
                    params=params,
                    json=json,
                    data=data,
                    method="GET",
                )
                record_exists = len(get_response["result"]) > 0
                num_retries += 1
                if num_retries > max_retries:
                    if raise_on_wait_expired:
                        raise HTTPError(f"Record not found after {max_retries} retries")
                    else:
                        return {"result": []}
                if method == "GET":
                    response = get_response

        if method != "DELETE":
            if type(response) == dict:
                return response
            else:
                return response.json()
        else:
            return response

    def _get_sys_property(self, property_name: str) -> str:
        """
        Get a sys_property from the instance.
        """
        property_value = self.table_api_call(
            table="sys_properties",
            params={"sysparm_query": f"name={property_name}", "sysparm_fields": "value"},
        )["result"][0]["value"]

        return property_value

    def check_is_installed(self):
        """
        Check if the ServiceNow instance is installed.
        Bascally, check if if the installation date is set.
        """
        property_name = "workarena.installation.date"
        try:
            self._get_sys_property(property_name)
        except Exception:
            raise RuntimeError(
                f"ServiceNow instance is most likey not installed. "
                "Please install the WorkArena plugin by running `workarena-install`.\n"
                "Alternatively, your credentials might not be correct. Please check them."
            )

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

    @property
    def release_version(self) -> str:
        """
        Get the release of the ServiceNow instance

        Returns:
        --------
        dict
            Information about the release of the ServiceNow instance

        """
        # XXX: Need to include the import here to avoid circular imports
        from .utils import ui_login

        keys = ["build name", "build date", "build tag", "connected to cluster node"]

        # We need to use playwright since the page is loaded dynamically
        # and its source doesn't contain the information we need
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            ui_login(self, page)
            page.goto(self.snow_url + "/stats.do")

            # The page contains a big list of information separated by <br> tags. Extract it.
            release_info = {
                key.strip(): value.strip()
                for x in page.content().lower().split("<br>")
                if ":" in x
                for key, value in [x.split(":", 1)]
                if key in keys
            }
            browser.close()

        return release_info
