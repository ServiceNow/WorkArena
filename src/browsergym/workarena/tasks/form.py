import json
import logging
import playwright.sync_api
import re

from english_words import get_english_words_set
from playwright.sync_api._generated import Page
from time import sleep
from typing import List, Tuple

from ..api.utils import (
    db_delete_from_table,
    table_api_call,
    table_column_info,
    HTTPError,
)
from .base import AbstractServiceNowTask
from ..config import (
    SNOW_BROWSER_TIMEOUT,
    CREATE_CHANGE_REQUEST_CONFIG_PATH,
    CREATE_HARDWARE_CONFIG_PATH,
    CREATE_INCIDENT_CONFIG_PATH,
    CREATE_PROBLEM_CONFIG_PATH,
    CREATE_USER_CONFIG_PATH,
)
from ..instance import SNowInstance
from .utils.form import fill_text


ENGLISH_WORDS = list(get_english_words_set(["web2"]))


class ServiceNowFormTask(AbstractServiceNowTask):
    def __init__(
        self,
        start_rel_url,
        instance: SNowInstance = None,
        extra_mandatory_fields: List = [],
        prohibited_fields: List = [],
    ) -> None:
        # The type of fields that we support interacting with
        self.supported_types = [
            "boolean",
            "choice",
            "email",
            "integer",
            "ph_number",
            "reference",
            "string",
        ]
        self.string_types = ["email", "ph_number", "string"]

        # Javascript variable names for the form API
        self.js_prefix = "gsft_main"
        self.js_api_forms = "g_form"
        self.form_js_selector = self.js_prefix + "." + self.js_api_forms

        # Extra mandatory fields (overriding the page specification)
        self.extra_mandatory_fields = extra_mandatory_fields

        # Prohibited fields: fields that we shouldn't interact with
        self.prohibited_fields = prohibited_fields

        super().__init__(instance=instance, start_rel_url=start_rel_url)

    def _get_form(self, page):
        """
        Loads a bunch of info about the form on a page into object variables

        """
        self._wait_for_ready(page)

        # Extract Glide table information
        logging.debug("Extracting Glide table metadata")
        # ... name of data table
        self.table_name = page.evaluate(f"{self.form_js_selector}.getTableName()")
        # ... expand reference fields
        # XXX: We need to expand reference fields and the referenced field is missing from the
        # form's client-side info so we are going to use the meta API to get that info.
        self.table_metadata = table_column_info(instance=self.instance, table=self.table_name)
        # ... augment with rendered metadata
        # XXX: Additional useful info is present in the rendered HTML. We extract it from there.
        for f in self.table_metadata:
            loc = page.frame(name=self.js_prefix).locator(f"#sys_display\.{self.table_name}\.{f}")
            if loc.count() > 0:
                # Check if the field is dependent on another field
                self.table_metadata[f]["dependent_on_field"] = loc.first.get_attribute(
                    "data-dependent"
                )

        # Get the table's pretty-printed label
        logging.debug("Extracting table pretty-printed title")
        self.table_label = table_api_call(
            instance=self.instance,
            table="sys_db_object",
            params={
                "sysparm_query": f"name={self.table_name}",
            },
        )["result"][0]["label"].lower()

        # Get the form fields
        logging.debug("Extracting valid form fields")
        editable_fields = page.evaluate(f"{self.form_js_selector}.getEditableFields()")
        self.fields = {
            f["fieldName"]: f
            for f in page.evaluate(f"{self.form_js_selector}.elements")
            if f["fieldName"] in editable_fields
            and f["fieldName"] not in self.prohibited_fields
            and f["type"] in self.supported_types
            and self.table_metadata[f["fieldName"]].get(
                "dependent_on_field", ""
            )  # Don't add a field that depends on one that we'll edit
            not in editable_fields
        }
        # ... and their labels
        for f in self.fields:
            self.fields[f]["label"] = page.evaluate(f"{self.form_js_selector}.getLabelOf('{f}')")

        # Split them into mandatory and optional
        self.mandatory_fields = [f for f in self.fields.keys() if self.fields[f]["mandatory"]]
        self.optional_fields = [f for f in set(self.fields.keys()) - set(self.mandatory_fields)]

        # Sanity check
        assert len(self.fields) > 0, "No editable fields found."
        assert set(self.extra_mandatory_fields) <= set(
            self.mandatory_fields
        ), "Some extra mandatory fields are not mandatory in the form."
        assert all(
            f not in self.fields for f in self.prohibited_fields
        ), "Some prohibited fields are editable in the form."

    def _preprocess_fields(self, field, value):
        """
        Do some preprocessing on loaded fields

        For example, we don't want to load old dates since they won't match newly created entries

        """
        logging.debug(f"Preprocessing field {field}")
        if field not in self.fields:
            return value

        field_type = self.table_metadata[field]["type"]

        # Extract display values for reference fields
        if field_type == "reference" and isinstance(value, dict):
            value = value["display_value"]

        # Remove date/time/username from journal entries
        elif field_type == "journal_input" and re.match(
            r"^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01]) ([01]\d|2[0-3]):([0-5]\d):([0-5]\d) - .*",
            value,
        ):
            value = value[value.index("\n") + 1 :].strip().replace("\n", "").replace("\r", "")

        # Any other text-based input
        elif field_type in self.string_types:
            if value is not None:
                value = value.strip().replace("\n", "").replace("\r", "")

        return value

    def _wait_for_ready(self, page: Page) -> None:
        """
        Waits for the main iframe to be fully loaded

        """
        logging.debug(f"Waiting for {self.js_prefix} to be fully loaded")
        page.wait_for_function(
            f"typeof window.{self.js_prefix} !== 'undefined' && window.{self.js_prefix}.WORKARENA_LOAD_COMPLETE"
        )
        logging.debug(f"Detected {self.js_prefix} ready")

        logging.debug("Waiting for Glide form API to be available")
        page.wait_for_function(f"window.{self.form_js_selector}")
        logging.debug("Detected Glide form API ready")

        logging.debug("Waiting for Glide tabs API to be available")
        page.wait_for_function(f"typeof window.{self.js_prefix}.g_tabs2Sections !== 'undefined'")
        logging.debug("Detected Glide tabs API ready")

    def pre_setup(self, seed: int, page: Page):
        super().pre_setup(seed, page)

        # Register a few initialization scripts
        self._add_init_scripts_to_context_and_reload(
            page,
            [
                "registerGsftMainLoaded();",
                # ... Mark the extra mandatory fields as such
                f"""
            // Check that the script is running in the main iframe
            if (window.frameElement?.id === '{self.js_prefix}') {{
                waLog('Setting mandatory fields');
                waitForCondition(() => typeof {self.js_api_forms} !== 'undefined', 100)
                .then(waitForCondition(() => typeof window.WORKARENA_LOAD_COMPLETE !== 'undefined' && window.WORKARENA_LOAD_COMPLETE, 100)
                    .then(
                        function (){{
                            {';'.join([self.js_api_forms + '.setMandatory("' + f + '", true)' for f in self.extra_mandatory_fields])}
                            waLog('Mandatory fields set successfully.');
                        }}
                    )
                );
            }}
            """,
            ],
        )

        self._get_form(page)


class GenericNewRecordTask(ServiceNowFormTask):
    """
    Generic task to create a new record in a table using a Glide form.

    Parameters:
    -----------
    form_url: str
        The URL of the form to use to create the record.
    instance: SNowInstance
        The instance on which to create the record.
    extra_mandatory_fields: List
        List of fields that should be marked as mandatory in the form (overrides the page specification).
    unique_valued_fields: dict
        Dictionary of fields that should have a unique value. Keys are the field names and values are functions
        used to make the fields unique (e.g., appending self.unique).
    min_fields: int
        Minimum number of fields to fill (except if mandatory is more).
    max_fields: int
        Maximum number of fields to fill (except if mandatory is more).
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/create_hardware_asset_task.json
        for an example of a configuration file.
    config_path:
        The path to the JSON file containing all configurations for the task. Provided by subclasses
    """

    def __init__(
        self,
        form_url: str,
        instance: SNowInstance = None,
        extra_mandatory_fields: List = [],
        prohibited_fields: List = [],
        unique_valued_fields: dict = {},
        min_fields: int = 5,
        max_fields: int = None,
        fixed_config: dict = None,
        config_path: str = None,
    ) -> None:
        super().__init__(
            instance=instance,
            start_rel_url=form_url,
            extra_mandatory_fields=extra_mandatory_fields,
            prohibited_fields=prohibited_fields,
        )
        self.form_url = form_url

        # Key in which the sys_id of the created record will be stored in the local storage
        self.session_sys_id_field = f"{id(self)}.record_sys_id"

        # Fields that should have a unique value (will append them with a uuid)
        self.unique_valued_fields = unique_valued_fields

        # Maximum number of fields to fill (except if mandatory is more)
        self.min_fields = min_fields
        self.max_fields = 999999999 if max_fields is None else max_fields

        # Fixed configuration
        self.fixed_config = fixed_config

        self.n_extra_fields = None
        self.template_record = None
        self.created_sysids = None
        if config_path:
            with open(config_path, "r") as f:
                self.all_configs = json.load(f)

    def setup(self, seed: int, page: Page) -> tuple[str, dict]:
        self.pre_setup(seed, page)
        self._run_init_scripts(page)
        assert self.all_configs is not None, "No configuration available for the task."
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)

        self.template_record = config["template_record"]
        self.task_fields = config["task_fields"]
        self.fields = config["fields"]

        self.created_sysids = []  # Used to track an

    def _run_init_scripts(self, page: Page) -> None:
        self._add_init_scripts_to_context_and_reload(
            page,
            [
                f"""
            // Check that the script is running in the main iframe
            if (window.frameElement?.id === '{self.js_prefix}') {{
                waLog('Attempting to override form submit function');
                waitForCondition(() => typeof {self.js_api_forms} !== 'undefined', 100)
                .then(waitForCondition(() => typeof gsftSubmit !== 'undefined', 100)
                    .then(
                        function overrideSubmit(){{
                            // Save the original function if it hasn't been saved yet
                            if(typeof old_gsftSubmit == 'undefined'){{
                                old_gsftSubmit = new Function('return ' + gsftSubmit.toString())();
                                waLog('Saved original submit function');
                            }}

                            // Override the function to save the sys_id in the local storage
                            gsftSubmit = function(control, form, action_name) {{
                                localStorage['{self.session_sys_id_field}'] = {self.js_api_forms}.getUniqueValue();
                                old_gsftSubmit(control, form, action_name);
                            }};
                            waLog('Patched submit function. All done.');
                        }}
                    )
                );
            }}
            """
            ],
        )

    def _generate_random_config(self, seed: int, page: Page) -> None:
        """Generate a random configuration for the task."""
        super().setup(seed, page)
        self._run_init_scripts(page)
        # Determine task fields
        logging.debug("Determining task fields")
        # ... check that we have enough fields
        assert (
            len(self.fields) >= self.min_fields
        ), f"Only {len(self.fields)} fields are available and task expects at least {self.min_fields} to fill."
        # ... make sure we select a number of fields within the allowed range
        self.n_extra_fields = self.random.randint(
            self.min_fields - len(self.mandatory_fields),
            max(
                0,
                min(
                    len(self.optional_fields),
                    self.max_fields - len(self.mandatory_fields),
                ),
            )
            + 1,
        )
        # ... select final fields
        self.task_fields = (
            self.mandatory_fields
            + self.random.choice(
                list(self.optional_fields), size=self.n_extra_fields, replace=False
            ).tolist()
        )

        # Load a random record from the database and use its values as a template
        logging.debug("Loading a record from the database to use as a template")
        # ... build a query to find a record with non-empty mandatory fields
        query_non_empty_mandatory_fields = "^".join(
            [f"{field}ISNOTEMPTY" for field in self.mandatory_fields]
        )
        # ... find how many entries there are in the table
        n_entries = len(
            table_api_call(
                instance=self.instance,
                table=self.table_name,
                params={
                    "sysparm_fields": "sys_id",
                    "sysparm_query": query_non_empty_mandatory_fields,
                },
            )["result"]
        )
        assert n_entries > 0, "No entries found to serve as template for the task."
        # ... sample a random record
        self.template_record = table_api_call(
            instance=self.instance,
            table=self.table_name,
            params={
                "sysparm_limit": 1,
                "sysparm_offset": self.random.randint(0, n_entries),
                "sysparm_display_value": True,
                "sysparm_query": query_non_empty_mandatory_fields,
            },
        )["result"][0]
        # ... preprocess its fields
        self.template_record = {
            f: self._preprocess_fields(f, v) for f, v in self.template_record.items()
        }
        # ... make unique any field that must have a unique value
        for f, func in self.unique_valued_fields.items():
            self.template_record[f] = func(self.template_record[f])

        # Replace some field values
        for f in self.fields:
            if "choices" in self.table_metadata[f]:
                if (
                    # ... if the field has choices that are not available in the UI
                    self.template_record[f] not in self.table_metadata[f]["choices"].values()
                    or
                    # ... avoid empty values if there are other choices
                    (
                        (self.template_record[f] is None or self.template_record[f] == "")
                        and len(self.table_metadata[f]["choices"]) > 1
                    )
                ):
                    # XXX: We skip empty-string values because 1) they are not really interesting to
                    #      ask for since the agent doesn't have to do anything. They also cause issues
                    #      in the validation since they don't get saved properly to the database.
                    choices = [v for k, v in self.table_metadata[f]["choices"].items() if k != ""]
                    self.template_record[f] = self.random.choice(choices)
            elif self.table_metadata[f]["type"] in self.string_types:
                # ... if the field is a string, we want to make sure that it's not empty
                if self.template_record[f] == "":
                    if self.table_metadata[f]["type"] == "string":
                        self.template_record[f] = " ".join(
                            self.random.choice(ENGLISH_WORDS, size=5)
                        )
                    elif self.table_metadata[f]["type"] == "email":
                        self.template_record[f] = (
                            f"{'.'.join(self.random.choice(ENGLISH_WORDS, size=2))}@workarena.com"
                        )
                    elif self.table_metadata[f]["type"] == "ph_number":
                        self.template_record[f] = (
                            f"(514) {self.random.randint(100, 999)}-{self.random.randint(1000, 9999)}"
                        )

        # Make sure the value satisfies the max length for the field
        self.template_record = {
            f: (
                v[: self.table_metadata[f]["max_length"]]
                if isinstance(v, str) and self.table_metadata[f]["type"] in self.string_types
                else v
            )
            for f, v in self.template_record.items()
        }
        self.created_sysids = []

        # generate the goal
        goal = (
            f"Create a new {self.table_label} with "
            + " and ".join(
                [
                    f'a value of "{self.template_record[f]}"'
                    + f' for field "{self.fields[f]["label"]}"'
                    for f in self.task_fields
                ]
            )
            + "."
        )
        info = {}
        return goal, info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page, chat_messages)
        self._wait_for_ready(page)
        iframe = page.frame_locator(f'iframe[name="{self.js_prefix}"]')

        from tenacity import retry, stop_after_delay, retry_if_exception_type

        # Retry on TypeError since in very rare occasions, element evaluates to null, which raises a TypeError
        @retry(
            stop=stop_after_delay(SNOW_BROWSER_TIMEOUT // 1000),
            retry=retry_if_exception_type(TypeError),
        )
        def show_field_tab(field):
            """
            Finds the control that allows to show the section where a field is located
            and clicks on it.

            """
            section = page.evaluate(
                f"""() => {{
                    const element = {self.form_js_selector}.getElement('{field}');
                    const ancestors = element.ancestors();
                    for (let ancestor of ancestors) {{
                        // Ancestor IDs are of the form "section-<section name>"
                        if (ancestor.id.startsWith('section-')) {{
                            return ancestor.id;
                        }}
                    }}
                    return null;  // Return null if no matching ancestor is found
                }}"""
            )
            section_id = section.split("-")[-1]
            tab_sections = {
                s.split(".")[-1]: i
                for i, s in enumerate(page.evaluate(f"{self.js_prefix}.g_tabs2Sections.tabIDs"))
            }

            # If the section is not in the tabs do nothing (it's probably the main section)
            if section_id not in tab_sections:
                return

            page.evaluate(
                f"""{self.js_prefix}.g_tabs2Sections.tabsTabs[
                                                    {tab_sections[section_id]}
                                                ].element.click()"""
            )

        for field in self.task_fields:
            # Get the field's input control
            control = iframe.get_by_label(
                page.evaluate(f"{self.form_js_selector}.getLabelOf('{field}')"),
                exact=True,
            )

            # If the field is in a section, click on its header to make it visible
            show_field_tab(field)

            # Some fields are marked as string by the API but accept selection-based input
            # We use the select tag condition to match these fields. Others are marked as integers.
            if self.table_metadata[field]["type"] == "choice":
                control.select_option(str(self.template_record[field]))

            # Checkboxes
            elif self.table_metadata[field]["type"] == "boolean":
                control.set_checked(1 if self.template_record[field] == "true" else 0)

            # Any text-based input
            else:
                fill_text(
                    page=page,
                    iframe=iframe,
                    input_field=control,
                    value=self.template_record[field],
                )

        # Click on the submit button
        page.wait_for_timeout(1000)
        iframe.locator("#sysverb_insert").click()

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        """
        Caveat: we check only if the expected fields have the right value. We don't Check
                if there are extra fields that shouldn't be there. We could have issues
                matching other fields since calculation rules may have changed through time.
                Maybe we should assign a random value from our list of choices to the fields
                that are not part of the task.

        """
        self._wait_for_ready(page)

        # Retrieve the created record's sys_id from the session storage
        sys_id = page.evaluate("localStorage").get(self.session_sys_id_field, None)

        # Check that a record has actually been created
        if sys_id is None:
            logging.info("No record has been created.")
            return (
                0,
                False,
                "",
                {"message": "The form has not been submitted."},
            )

        # Add the sysid to the list of created sysids
        # This is used to clean up the database after the task is completed.
        self.created_sysids.append(sys_id)

        # Short sleep to make sure the data is saved in the DB
        # TODO: improve this (noted in issue 291)
        sleep(3)

        # Pull the record from the database
        record = table_api_call(
            instance=self.instance,
            table=self.table_name,
            params={
                "sysparm_query": f"sys_id={sys_id}",
                "sysparm_display_value": True,
            },
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
            if record[f] != self.template_record[f]:
                logging.info(
                    f'The field "{self.fields[f]["label"]}" has the wrong value. Expected: "{self.template_record[f]}", got: "{record[f]}".'
                )
                error_msg = (f'The field "{self.fields[f]["label"]}" has the wrong value.',)
                return (
                    0,
                    True,  # End episode (incorrect information pushed to the DB)
                    error_msg,
                    {"message": error_msg},
                )

        return 1, True, "Nice work, thank you!", {"message": "The record was successfully created."}

    def teardown(self) -> None:
        self._wait_for_ready(self.page)

        # Retrieve the current record's sys_id from the session storage
        sys_id = self.page.evaluate("localStorage").get(self.session_sys_id_field, None)

        # Also include any other sysid that was encountered in validation
        ids = set([sys_id] + self.created_sysids)

        for sys_id in ids:
            if sys_id is not None:
                try:
                    db_delete_from_table(
                        instance=self.instance, sys_id=sys_id, table=self.table_name
                    )
                except HTTPError:
                    # sys_id was stored in local storage (for submitted)
                    # but the record is absent from the database (probably invalid form)
                    pass


class CreateChangeRequestTask(GenericNewRecordTask):
    """
    Task to create a new change request in the system.

    """

    def __init__(self, instance=None, fixed_config: dict = None) -> None:
        super().__init__(
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/change_request.do",
            prohibited_fields=["chg_model", "state"],
            fixed_config=fixed_config,
            config_path=CREATE_CHANGE_REQUEST_CONFIG_PATH,
        )


class CreateIncidentTask(GenericNewRecordTask):
    """
    Task to create a new incident in the system.

    """

    def __init__(self, instance=None, fixed_config: dict = None) -> None:
        super().__init__(
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/incident.do",
            prohibited_fields=["state"],
            fixed_config=fixed_config,
            config_path=CREATE_INCIDENT_CONFIG_PATH,
        )


class CreateHardwareAssetTask(GenericNewRecordTask):
    """
    Task to create a new user in the system.

    """

    def __init__(self, instance=None, fixed_config: dict = None) -> None:
        super().__init__(
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/alm_hardware.do",
            prohibited_fields=["install_status"],
            extra_mandatory_fields=[
                "model",
                "model_category",
                "serial_number",
                "vendor",
            ],
            unique_valued_fields={"serial_number": lambda x: f"SN-{self.unique_id}"},
            fixed_config=fixed_config,
            config_path=CREATE_HARDWARE_CONFIG_PATH,
        )


class CreateProblemTask(GenericNewRecordTask):
    """
    Task to create a new problem in the system.

    """

    def __init__(self, instance=None, fixed_config: dict = None) -> None:
        super().__init__(
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/problem.do",
            prohibited_fields=["state", "first_reported_by_task"],
            fixed_config=fixed_config,
            config_path=CREATE_PROBLEM_CONFIG_PATH,
            # TODO: The last field is disabled because somehow the value is not in the autocomplete
            #       list even though it's in the database. I'm not sure why. It doesn't matter much
            #       since in the future we'll pre-generate tasks and keep only the ones where the
            #       cheat function works.
        )


class CreateUserTask(GenericNewRecordTask):
    """
    Task to create a new user in the system.

    """

    def __init__(self, instance=None, fixed_config: dict = None) -> None:
        super().__init__(
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/sys_user.do",
            extra_mandatory_fields=["user_name", "first_name", "last_name", "email"],
            unique_valued_fields={"user_name": lambda x: str(hash(x + self.unique_id))},
            fixed_config=fixed_config,
            config_path=CREATE_USER_CONFIG_PATH,
        )


__TASKS__ = [
    var
    for var in locals().values()
    if isinstance(var, type)
    and issubclass(var, GenericNewRecordTask)
    and var is not GenericNewRecordTask
]
