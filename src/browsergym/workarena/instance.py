import base64
import json
import logging
import os
import random
import requests
from itertools import cycle

from huggingface_hub import hf_hub_download
from huggingface_hub.utils import disable_progress_bars
from playwright.sync_api import sync_playwright
from typing import Optional

from .config import (
    INSTANCE_REPO_FILENAME,
    INSTANCE_REPO_ID,
    INSTANCE_REPO_TYPE,
    INSTANCE_XOR_SEED,
    REPORT_FILTER_PROPERTY,
    SNOW_BROWSER_TIMEOUT,
)


# Required to read the instance credentials
if not INSTANCE_XOR_SEED:
    raise ValueError("INSTANCE_XOR_SEED must be configured")


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ k for b, k in zip(data, cycle(key)))


def decrypt_instance_password(encrypted_password: str) -> str:
    """Decrypt a base64-encoded XOR-obfuscated password using the shared key."""

    cipher_bytes = base64.b64decode(encrypted_password)
    plain_bytes = _xor_cipher(cipher_bytes, INSTANCE_XOR_SEED.encode("utf-8"))
    return plain_bytes.decode("utf-8")


def encrypt_instance_password(password: str) -> str:
    """Helper to produce encrypted passwords for populating the instance file."""

    cipher_bytes = _xor_cipher(password.encode("utf-8"), INSTANCE_XOR_SEED.encode("utf-8"))
    return base64.b64encode(cipher_bytes).decode("utf-8")


def fetch_instances():
    """
    Load the latest instances from either a custom pool (SNOW_INSTANCE_POOL) or the gated HF dataset.
    """
    pool_path = os.getenv("SNOW_INSTANCE_POOL")
    if pool_path:
        path = os.path.expanduser(pool_path)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"SNOW_INSTANCE_POOL points to '{pool_path}', but the file does not exist."
            )
        logging.info("Loading ServiceNow instances from custom pool: %s", path)
    else:
        try:
            disable_progress_bars()
            path = hf_hub_download(
                repo_id=INSTANCE_REPO_ID,
                filename=INSTANCE_REPO_FILENAME,
                repo_type=INSTANCE_REPO_TYPE,
            )
            logging.info("Loaded ServiceNow instances from the default instance pool.")
        except Exception as e:
            raise RuntimeError(
                f"Could not access {INSTANCE_REPO_ID}/{INSTANCE_REPO_FILENAME}. "
                "Make sure you have been granted access to the gated repo and that you are "
                "authenticated (run `huggingface-cli login` or set HUGGING_FACE_HUB_TOKEN)."
            ) from e

    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    for entry in entries:
        entry["url"] = entry["u"]
        entry["password"] = decrypt_instance_password(entry["p"])
        del entry["u"]
        del entry["p"]

    return entries


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
            The URL of a SNow instance. When omitted, the constructor first looks for SNOW_INSTANCE_URL and falls back
            to a random instance from the benchmark's instance pool if the environment variable is not set.
        snow_credentials: (str, str)
            The username and password used to access the SNow instance. When omitted, environment variables
            SNOW_INSTANCE_UNAME/SNOW_INSTANCE_PWD are used if set; otherwise, a random instance from the benchmark's
            instance pool is selected.

        """
        # try to get these values from environment variables if not provided
        if snow_url is None or snow_credentials is None:

            # Check if all required environment variables are set and if yes, fetch url and credentials from there
            if (
                "SNOW_INSTANCE_URL" in os.environ
                and "SNOW_INSTANCE_UNAME" in os.environ
                and "SNOW_INSTANCE_PWD" in os.environ
            ):
                snow_url = os.environ["SNOW_INSTANCE_URL"]
                snow_credentials = (
                    os.environ["SNOW_INSTANCE_UNAME"],
                    os.environ["SNOW_INSTANCE_PWD"],
                )

            # Otherwise, load all instances and select one randomly
            else:
                instances = fetch_instances()
                if not instances:
                    raise ValueError(
                        f"No instances found in the dataset {INSTANCE_REPO_ID}. Please provide instance details via parameters or environment variables."
                    )
                instance = random.choice(instances)
                snow_url = instance["url"]
                snow_credentials = ("admin", instance["password"])

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

    @property
    def report_filter_config(self) -> dict:
        """
        Get the report filter configuration from the ServiceNow instance.

        Returns:
        --------
        dict
            The report filter configuration, or an empty dictionary if not found.

        """
        from .api.system_properties import (
            get_sys_property,
        )  # Import here to avoid circular import issues

        try:
            config = get_sys_property(self, REPORT_FILTER_PROPERTY)
            config = json.loads(config)
            return config
        except Exception:
            return None
