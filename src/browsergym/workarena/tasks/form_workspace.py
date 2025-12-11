from .form import CreateIncidentTask, CreateProblemTask
from playwright.sync_api import Page
from .utils.utils import prettyprint_enum
from .form import GenericNewRecordTask
from importlib import resources
from ..config import data_files
import logging
from typing import Tuple
from ..api.utils import table_api_call
import re
import urllib.parse as parse
from ..utils import url_login
from typing import List


class GenericCreateWorkspaceTask(GenericNewRecordTask):

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get the task configuration
        assert self.all_configs is not None, "No configuration available for the task."
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        self.config = config
        # If fixed_config is not None we already set the required attributes in the constructor
        if self.fixed_config is None:
            self._set_required_config_attributes(config)
        self.protected_fields = self.task_fields

        if "goal" in self.config:
            goal = self.config["goal"]
            # replace placeholders
            goal = goal.format(**self.template_record)
        else:
            goal = (
                f"In the Service Operations workspace, create a new {self.table_label} with "
                + prettyprint_enum(
                    [
                        f'a value of "{self.template_record[f]}"'
                    + f' for field "{self.config["fields"][f]}"'
                    for f in self.task_fields
                ]
            )
                + "."
            )
        info = {}

        return goal, info

    def validate(
        self, page: Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        # get the url of the current page
        if f"sow/record/{self.table_name}/" not in page.url:
            return 0.0, False, "", {"message": f"The assistant is not in the workspace {self.table_label} form."}
        else:
            # Get the string after sow/record/<table_name>/ in the url but before the /params
            # This may not be a valid sys id, which does not matter as no record will be found with it
            sys_id = page.url.split(f"sow/record/{self.table_name}/")[1].split("/params")[0]

            # Check that a record has actually been created
            if sys_id is None:
                logging.info("No record has been created or the form has not been submitted.")
                return (
                    0,
                    False,
                    "",
                    {"message": "No record has been created or the form has not been submitted."},
                )
            
            print(f"Found sys_id {sys_id} in the URL")

            # Add the sysid to the list of created sysids
            # This is used to clean up the database after the task is completed.
            self.created_sysids.append(sys_id)

            # Pull the record from the database
            # XXX: It's possible that the record is not found, e.g., if form submission was rejected due to client-side
            #      validation errors. In this case, we should not raise an error and simply consider that no record was
            #      created. This is non-terminal for the task.
            record = table_api_call(
                instance=self.instance,
                table=self.table_name,
                params={
                    "sysparm_query": f"sys_id={sys_id}",
                    "sysparm_display_value": True,
                },
                wait_for_record=True,
                max_retries=20,  # Wait up to 10 seconds
                raise_on_wait_expired=False,
            )["result"]

            # This can happen if the form was submitted but was rejected due to invalid inputs (e.g., missing mandatory fields)
            if len(record) == 0:
                logging.info(
                    "The record was not found in the database. Perhaps the form was not submitted correctly. "
                    + sys_id,
                )
                return (
                    0,
                    False,
                    "",
                    {
                        "message": "The record was not found in the database. Perhaps the form was not submitted correctly."
                    },
                )

            # Extract display values for reference fields
            record = {
                f: v if not isinstance(v, dict) else v["display_value"] for f, v in record[0].items()
            }

            # Check that the record matches the expected values
            for f in self.task_fields:
                if record[f].strip() != self.template_record[f].strip():
                    error_msg = f'The field "{self.config["fields"][f]}" has the wrong value. Expected: "{self.template_record[f].strip()}", got: "{record[f].strip()}".'
                    logging.info(error_msg)
                    return (
                        0,
                        False, # False because we should let the agent continue trying
                        error_msg,
                        {"message": error_msg},
                    )

            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "The record was successfully created."},
            )

    def _wait_for_ready(self, page: Page, iframe_only=False) -> None:
        """
        Waits for the main iframe and APIs to be fully loaded

        Parameters:
        ----------
        page: playwright.sync_api.Page
            The page on which to wait for the iframe to be loaded
        iframe_only: bool
            If True, only wait for the iframe to be loaded. If False, also wait for the APIs to be available.

        """
        logging.debug(f"Waiting for {self.js_prefix} to be fully loaded")
        try:
            page.wait_for_function(
                f"typeof window.{self.js_prefix} !== 'undefined' && window.{self.js_prefix}.WORKARENA_LOAD_COMPLETE",
            )
        except:
            page.wait_for_load_state("networkidle")
            return
        logging.debug(f"Detected {self.js_prefix} ready")


class CreateWorkspaceIncidentTask(CreateIncidentTask, GenericCreateWorkspaceTask):
    config_path = str(
        resources.files(data_files).joinpath("task_configs/create_workspace_incident_task.json")
    )

    def __init__(self, seed: int = None,
        instance=None,
        fixed_config: dict = None,
        check_record_created=True,
        **kwargs) -> None:

        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            check_record_created=check_record_created)
        
        # Force starting at the homepage
        self.start_url = self.instance.snow_url


class CreateWorkspaceProblemTask(CreateProblemTask, GenericCreateWorkspaceTask):
    config_path = str(
        resources.files(data_files).joinpath("task_configs/create_workspace_problem_task.json")
    )
    
    def __init__(self, seed: int = None,
        instance=None,
        fixed_config: dict = None,
        check_record_created=True,
        **kwargs) -> None:

        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            check_record_created=check_record_created)
        
        # Force starting at the homepage
        self.start_url = self.instance.snow_url


class CreateTransferOrderTask(GenericCreateWorkspaceTask):
    config_path = str(
        resources.files(data_files).joinpath("task_configs/create_transfer_order_task.json")
    )

    def __init__(self, seed: int = None,
        instance=None,
        fixed_config: dict = None,
        check_record_created=True,
        **kwargs) -> None:

        GenericNewRecordTask.__init__(
            self,
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            check_record_created=check_record_created,
            table_label="Transfer Order",
            form_url="/now/nav/ui/classic/params/target/alm_transfer_order.do"
        )

        self.__dict__.update(kwargs)
        
        # Force starting at the homepage
        self.start_url = self.instance.snow_url
        self.created_sys_id = None

    def start(self, page: Page) -> None:
        # Overriding start because calling self._get_form(page) in the parent class gives an error
        logging.debug("Navigating to task start page")

        # Authenticate
        url_login(
            instance=self.instance,
            page=page,
        )

        # Navigate to the task's url
        page.goto(self.start_url)
        self._wait_for_ready(page)

    def get_init_scripts(self) -> List[str]:
       # Override this to avoid changing functionality of submit button
        return []

    def validate(
        self, page: Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        # Attempt to get the sys id of the record being created
        def extract_sys_id(url: str) -> str | None:
            """
            Return the 32-hex sys_id from a ServiceNow URL, or None if not found.
            Handles encoded target URLs like .../params/target/incident.do%3Fsys_id%3D<id>
            """
            # Unquote repeatedly (some SN URLs are doubly-encoded)
            for _ in range(3):
                new = parse.unquote(url)
                if new == url:
                    break
                url = new
            
            m = re.search(r"(?:[?&])sys_id=([0-9a-f]{32})", url, re.IGNORECASE)
            return m.group(1) if m else None

        sys_id = extract_sys_id(page.url)

        # If we have not found a sys_id yet, or if the sys_id has changed, we consider that a new record has been created
        if not self.created_sys_id or self.created_sys_id != sys_id:
            self.created_sys_id = sys_id
            # TODO this is not reliable as the agent could have just opened another record to view, which means we would consider it as a new record, and delete it
            # Keep track of all created sysids, so we can delete them after
            self.created_sysids.append(sys_id)

        if not self.created_sys_id:
            return 0.0, False, "", {"message": "No record has been created or the form has not been submitted."}
        else:
            logging.info(f"Found sys_id {self.created_sys_id} in the URL")

            # Add the sysid to the list of created sysids
            # This is used to clean up the database after the task is completed.
            
            # Pull the record from the database
            # XXX: It's possible that the record is not found, e.g., if form submission was rejected due to client-side
            #      validation errors. In this case, we should not raise an error and simply consider that no record was
            #      created. This is non-terminal for the task.
            record = table_api_call(
                instance=self.instance,
                table=self.table_name,
                params={
                    "sysparm_query": f"sys_id={self.created_sys_id}",
                    "sysparm_display_value": True,
                },
                wait_for_record=True,
                max_retries=20,  # Wait up to 10 seconds
                raise_on_wait_expired=False,
            )["result"]

            # This can happen if the form was submitted but was rejected due to invalid inputs (e.g., missing mandatory fields)
            if len(record) == 0:
                logging.info(
                    "The record was not found in the database. Perhaps the form was not submitted correctly. "
                    + sys_id,
                )
                return (
                    0,
                    False,
                    "",
                    {
                        "message": "The record was not found in the database. Perhaps the form was not submitted correctly."
                    },
                )

            # Extract display values for reference fields
            record = {
                f: v if not isinstance(v, dict) else v["display_value"] for f, v in record[0].items()
            }

            # We only check a subset of fields here as the rest are in another table
            for f in self.config["task_fields_transfer_order"]:
                if record[f].strip() != self.template_record[f].strip():
                    error_msg = f'The field "{self.config["fields"][f]}" has the wrong value. Expected: "{self.template_record[f].strip()}", got: "{record[f].strip()}".'
                    logging.info(error_msg)
                    return (
                        0,
                        False, # False because we should let the agent continue trying
                        error_msg,
                        {"message": error_msg},
                    )

            logging.info("The transfer order record was successfully created.")

            # We have gotten the transfer order fields right. Now let's look at whether we also have the transfer order lines right
            lines_record = table_api_call(
                instance=self.instance,
                table="alm_transfer_order_line",
                params={
                    "sysparm_query": f"transfer_order.sys_id={self.created_sys_id}",
                    "sysparm_display_value": True,
                },
                wait_for_record=True,
                max_retries=20,  # Wait up to 10 seconds
                raise_on_wait_expired=False,
            )["result"]

            if len(lines_record) == 0:
                error_msg = "The transfer order lines were not found in the database. We are missing some fields."
                logging.info(error_msg)
                return (
                    0,
                    False, # False because we should let the agent continue trying
                    error_msg,
                    {"message": error_msg},
                )

            num_expected_transfer_order_lines = self.config.get("num_expected_transfer_order_lines", 1)

            if len(lines_record) != num_expected_transfer_order_lines:
                error_msg = f"Found {len(lines_record)} transfer order lines, expected {num_expected_transfer_order_lines}."
                logging.info(error_msg)
                return (
                    0,
                    False, # False because we should let the agent continue trying
                    error_msg,
                    {"message": error_msg},
                )

            # Verify expected fields in transfer order lines
            for line in lines_record:
                line = {
                    f: v if not isinstance(v, dict) else v["display_value"] for f, v in line.items()
                }

                for f in self.config["task_fields_transfer_order_line"]:
                    if line[f].strip() != self.template_record[f].strip():
                        error_msg = f'The field "{self.config["fields"][f]}" has the wrong value. Expected: "{self.template_record[f].strip()}", got: "{line[f].strip()}".'
                        logging.info(error_msg)
                        return (
                            0,
                            False, # False because we should let the agent continue trying
                            error_msg,
                            {"message": error_msg},
                        )

            # TODO need to delete transfer order lines also!
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "The record was successfully created."},
            )

            
__TASKS__ = [CreateWorkspaceIncidentTask, CreateWorkspaceProblemTask, CreateTransferOrderTask]