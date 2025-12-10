from .form import CreateIncidentTask, CreateProblemTask
from playwright.sync_api import Page
from .utils.utils import prettyprint_enum
from .form import GenericNewRecordTask
from importlib import resources
from ..config import data_files
import logging
from typing import Tuple
from ..api.utils import table_api_call


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
    
            
__TASKS__ = [CreateWorkspaceIncidentTask, CreateWorkspaceProblemTask]