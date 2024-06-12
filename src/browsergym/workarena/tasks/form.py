import inspect
import json
import logging
import playwright.sync_api
import re

from collections import OrderedDict
from english_words import get_english_words_set
from faker import Faker

fake = Faker()
from playwright.sync_api._generated import Page
from tenacity import retry, stop_after_delay, retry_if_exception_type
from time import sleep
from typing import List, Tuple
from urllib import parse

from .base import AbstractServiceNowTask
from .comp_building_block import CompositionalBuildingBlockTask

from ..api.utils import (
    db_delete_from_table,
    table_api_call,
    table_column_info,
    HTTPError,
)
from ..config import (
    SNOW_BROWSER_TIMEOUT,
    # Paths to the configuration files
    CREATE_CHANGE_REQUEST_CONFIG_PATH,
    CREATE_HARDWARE_CONFIG_PATH,
    CREATE_INCIDENT_CONFIG_PATH,
    CREATE_PROBLEM_CONFIG_PATH,
    CREATE_USER_CONFIG_PATH,
    # Paths to the expected fields files
    EXPECTED_CHANGE_REQUEST_FORM_FIELDS_PATH,
    EXPECTED_HARDWARE_FORM_FIELDS_PATH,
    EXPECTED_INCIDENT_FORM_FIELDS_PATH,
    EXPECTED_PROBLEM_FORM_FIELDS_PATH,
    EXPECTED_USER_FORM_FIELDS_PATH,
    EXPECTED_REQUEST_ITEM_FORM_FIELDS_PATH,
)
from ..instance import SNowInstance
from .utils.form import fill_text
from .utils.utils import check_url_suffix_match, prettyprint_enum


ENGLISH_WORDS = list(get_english_words_set(["web2"]))


class ServiceNowFormTask(AbstractServiceNowTask):
    """
    Generic task for record manipulation (create/edit) in a table using a Glide form.

    Class attributes:
    -----------------
    config_path: str
        Path to the JSON file containing all possible configurations for the task. Defined in subclasses
    expected_fields_path: str
        Path to the JSON file containing all expected fields for the task. Defined in subclasses

    Parameters:
    -----------------
    form_url: str
        The URL of the form to use to create the record.
    instance: SNowInstance
        The instance on which to create the record.
    extra_mandatory_fields: List
        List of fields that should be marked as mandatory in the form (overrides the page specification).
    unique_valued_fields: dict
        Dictionary of fields that should have a unique value. Keys are the field names and values are functions
        used to make the fields unique (e.g., appending self.unique).
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/create_hardware_asset_task.json
        for an example of a configuration file.
    check_record_created: bool
        Whether to check if the record is created in cheat. This step uses the localStorage to get the sys_id, which is None when creating multiple forms. Hence, we bypass this step in the cheat.
    """

    config_path = None
    expected_fields_path = None

    def __init__(
        self,
        form_url: str,
        table_label: str,
        instance: SNowInstance = None,
        extra_mandatory_fields: List = [],
        prohibited_fields: List = [],
        unique_valued_fields: dict = {},
        fixed_config: dict = None,
        check_record_created: bool = True,
        seed: int = None,
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
        self.table_metadata = None
        self.fields = None
        self.mandatory_fields = None
        self.optional_fields = None

        super().__init__(seed=seed, instance=instance, start_rel_url=form_url)

        self.form_url = form_url

        # Table pretty printed name
        self.table_label = table_label
        self.table_name = self.form_url.split("/")[-1].split(".do")[0]

        # Key in which the sys_id of the created record will be stored in the local storage
        self.session_sys_id_field = f"{id(self)}.record_sys_id"

        # Fields that should have a unique value (will append them with a uuid)
        self.unique_valued_fields = unique_valued_fields

        # Fixed configuration
        # We set the task fields, template record and created sysids to allow for easy access in compositional task creation
        self.fixed_config = fixed_config
        self.template_record = None
        self.task_fields = None
        self.fields = None
        self.protected_fields = None  # Fields that should not be edited
        if fixed_config is not None:
            self._set_required_config_attributes(fixed_config)

        self.n_extra_fields = None
        self.created_sysids = []
        if self.config_path:
            self.all_configs = self.all_configs()
        if self.expected_fields_path:
            with open(self.expected_fields_path, "r") as f:
                self.expected_fields = json.load(f)
        self.check_record_created = check_record_created

    @classmethod
    def all_configs(cls) -> List[dict]:
        with open(cls.config_path, "r") as f:
            return json.load(f)

    def _get_form(self, page):
        """
        Loads a bunch of info about the form on a page into object variables
        """
        # Extract Glide table information
        logging.debug("Extracting Glide table metadata")
        # ... expand reference fields
        # XXX: We need to expand reference fields and the referenced field is missing from the
        # form's client-side info so we are going to use the meta API to get that info.
        self.table_metadata = table_column_info(instance=self.instance, table=self.table_name)
        # ... augment with rendered metadata
        # XXX: Additional useful info is present in the rendered HTML. We extract it from there.
        for f in self.table_metadata:
            loc = page.frame(name=self.js_prefix).locator(f"#sys_display.{self.table_name}.{f}")
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

    def _get_fields(self, page: Page) -> None:
        """
        Get the form fields; split them into mandatory and optional
        """
        page.wait_for_function(
            f"typeof window.{self.js_prefix} !== 'undefined' && window.{self.js_prefix}.WORKARENA_LOAD_COMPLETE",
        )

        # Get the form fields
        def is_field_visible(field):
            return page.evaluate(
                f"""
                {self.form_js_selector}.isVisible(
                    {self.form_js_selector}.getGlideUIElement('{field}'),
                    {self.form_js_selector}.getControl('{field}')
                );"""
            )

        logging.debug("Extracting valid form fields")
        editable_fields = page.evaluate(f"{self.form_js_selector}.getEditableFields()")
        field_elements = page.evaluate(f"{self.form_js_selector}.elements")
        all_fields = [f["fieldName"] for f in field_elements]
        self.fields = {
            f["fieldName"]: f
            for f in field_elements
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
        assert len(self.fields) > 0, "No fields found on page."
        assert len(editable_fields) > 0, "No editable fields found on page."
        # ... check that the script that marks some fields as mandatory worked
        assert set(self.extra_mandatory_fields) <= set(
            self.mandatory_fields
        ), "Some extra mandatory fields are not mandatory in the form."
        # ... check that the script that makes some fields read-only worked
        assert all(
            f not in self.fields for f in self.prohibited_fields
        ), "Some prohibited fields are editable in the form."
        # ... check that all the fields that the config expects are present and that extra fields are not visible
        all_visible_fields = set([f for f in all_fields if is_field_visible(f)])
        expected_visible_fields = set([f for f in self.expected_fields if is_field_visible(f)])
        set_diff = all_visible_fields.union(
            expected_visible_fields
        ) - all_visible_fields.intersection(expected_visible_fields)
        assert (
            len(set_diff) == 0
        ), f"The fields {set_diff} are either missing or unexpectedly visible on the form. Re-run 'workarena-install' to correct this."

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

        if not iframe_only:
            logging.debug("Waiting for Glide form API to be available")
            page.wait_for_function(f"window.{self.form_js_selector}")
            logging.debug("Detected Glide form API ready")

            logging.debug("Waiting for Glide tabs API to be available")
            page.wait_for_function(
                f"typeof window.{self.js_prefix}.g_tabs2Sections !== 'undefined'"
            )
            logging.debug("Detected Glide tabs API ready")

    def get_init_scripts(self) -> List[str]:
        # Extract expected URL suffix
        url_suffix = parse.urlparse(self.start_url).path.split("/")[-1]
        url_suffix = self.table_name

        # Add a few initialization scripts
        return super().get_init_scripts() + [
            "registerGsftMainLoaded();",
            # ... Mark the extra mandatory fields as such
            f"""
                function addFormMandatoryFields() {{
                    waLog('Setting mandatory fields', 'addFormMandatoryFields');
                    {";".join([f"{self.js_api_forms}.setMandatory('{f}', true)" for f in self.extra_mandatory_fields])}
                    waLog('Mandatory fields set successfully.', 'addFormMandatoryFields');
                }}

                runInGsftMainOnlyAndProtectByURL(addFormMandatoryFields, '{url_suffix}');
                """,
            f"""
                function patchSubmitButton() {{
                    waLog('Attempting to override form submit function', 'patchSubmitButton');
                    // Save the original function if it hasn't been saved yet
                    if(typeof old_gsftSubmit == 'undefined'){{
                        old_gsftSubmit = new Function('return ' + gsftSubmit.toString())();
                        waLog('Saved original submit function', 'patchSubmitButton');
                    }}

                    // Override the function to save the sys_id in the local storage
                    gsftSubmit = function(control, form, action_name) {{
                        localStorage['{self.session_sys_id_field}'] = {self.js_api_forms}.getUniqueValue();
                        old_gsftSubmit(control, form, action_name);
                    }};
                    waLog('Patched submit function. All done.', 'patchSubmitButton');
                }}

                runInGsftMainOnlyAndProtectByURL(patchSubmitButton, '{url_suffix}');
                """,
            # Ensure that only the expected fields are changed
            f"""
                function monitorChangeOnFields() {{
                    let predefinedList = {json.dumps(self.protected_fields)};
                    console.log('Predefined list: ' + predefinedList);
                    document.querySelectorAll("input, select, textarea").forEach((e) => {{
                        // Get the field name - some fields are like incident.xyz.field_name
                        let fieldName = e.name.split('.').pop();
                        if (!predefinedList.includes(fieldName)) {{
                            e.addEventListener("change", () => {{
                                window.WORKARENA_BAD_FIELD_CHANGED = true;
                                console.log("Field " + e.name + " changed and was not expected to.");
                            }})
                            waLog('Added change listener to field ' + e.name, 'monitorChangeOnFields');
                        }}
                    }})
                }}

                runInGsftMainOnlyAndProtectByURL(monitorChangeOnFields, '{url_suffix}');
            """,
        ]

    def start(self, page: Page) -> None:
        super().start(page)
        self._wait_for_ready(page)
        self._get_form(page)

    def _fill_fields(
        self,
        page: Page,
        iframe: playwright.sync_api.Frame,
        task_fields: List[str],
        update: bool = False,
    ) -> None:
        """
        Fill the fields in the form with the values from the template record. The fields to fill are specified in the
        task_fields list. Update is a flag that indicates if the task is an update task.
        """
        # XXX We need to ensure the table metadata as well as fields are set
        # before we can proceed with the cheat function
        if self.table_metadata is None:
            self._get_form(page)
        if self.fields is None:
            self._get_fields(page)

        # From now on, we assume we are on the form page
        self._wait_for_ready(page)

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

            page.evaluate_handle(
                f"""{self.js_prefix}.g_tabs2Sections.tabsTabs[
                                                    {tab_sections[section_id]}
                                                ].element"""
            ).click(force=True)

        for field in task_fields:
            # Get the field's input control
            control = iframe.get_by_label(
                page.evaluate(f"{self.form_js_selector}.getLabelOf('{field}')"),
                exact=True,
            )
            if control.count() > 1:
                control = control.nth(0)
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
        if update:
            iframe.locator("#sysverb_update").click()
        else:
            iframe.locator("#sysverb_insert").click()

        # Check if the record was created
        if self.check_record_created:
            # This does not work if multiple forms are created at once. The localStorage returns null after the first form
            for attempt in range(5):
                # in update tasks, the sys_id is already known as the asset is created from the start
                if update:
                    sys_id = self.record_sys_id
                else:
                    sys_id = page.evaluate("localStorage").get(self.session_sys_id_field, None)

                # Pull the record from the database
                record = table_api_call(
                    instance=self.instance,
                    table=self.table_name,
                    params={
                        "sysparm_query": f"sys_id={sys_id}",
                        "sysparm_display_value": True,
                    },
                )["result"]
                if len(record) > 0:
                    break
                page.wait_for_timeout(1500)
                if attempt == 4:
                    raise ValueError("The record was not created.")

    def _set_required_config_attributes(self, config: dict) -> None:
        """
        Set the required attributes for the task configuration.
        """
        # XXX Warning: Some subclasses may expect a specific order of elements
        self.template_record = config["template_record"]
        for f, func in self.unique_valued_fields.items():
            self.template_record[f] = func(self.template_record[f])
        self.task_fields = config["task_fields"]

    def get_new_field_value(self, field: str, template_record: dict, table_metadata: dict) -> str:
        """
        Generate a new value for a field based on the field type.
        """
        new_value = template_record[
            field
        ]  # Default to the template value in case the task field is not of the supported types
        if field in self.unique_valued_fields:
            return new_value
        if "choices" in table_metadata[field]:
            if (
                # ... if the field has choices that are not available in the UI
                template_record[field] not in table_metadata[field]["choices"].values()
                or
                # ... avoid empty values if there are other choices
                (
                    (template_record[field] is None or template_record[field] == "")
                    and len(table_metadata[field]["choices"]) > 1
                )
            ):
                # XXX: We skip empty-string values because 1) they are not really interesting to
                #      ask for since the agent doesn't have to do anything. They also cause issues
                #      in the validation since they don't get saved properly to the database.
                choices = [v for k, v in table_metadata[field]["choices"].items() if k != ""]
                new_value = self.random.choice(choices)
        elif table_metadata[field]["type"] in self.string_types:
            # ... if the field is a string, we want to make sure that it's not empty

            if table_metadata[field]["type"] == "string":
                new_value = " ".join(self.random.choice(ENGLISH_WORDS, size=5))
            elif table_metadata[field]["type"] == "email":
                new_value = f"{'.'.join(self.random.choice(ENGLISH_WORDS, size=2))}@workarena.com"
            elif table_metadata[field]["type"] == "ph_number":
                new_value = (
                    f"(514) {self.random.randint(100, 999)}-{self.random.randint(1000, 9999)}"
                )

        return new_value


class GenericNewRecordTask(ServiceNowFormTask):
    """
    Generic task to create a new record in a table using a Glide form.

    Parameters:
    -----------
    min_fields: int
        Minimum number of fields to fill (except if mandatory is more).
    max_fields: int
        Maximum number of fields to fill (except if mandatory is more).
    """

    config_path = None
    expected_fields_path = None

    def __init__(
        self,
        form_url: str,
        table_label: str,
        instance: SNowInstance = None,
        extra_mandatory_fields: List = [],
        prohibited_fields: List = [],
        unique_valued_fields: dict = {},
        min_fields: int = 5,
        max_fields: int = None,
        fixed_config: dict = None,
        seed: int = None,
        check_record_created: bool = True,
    ) -> None:
        super().__init__(
            seed=seed,
            form_url=form_url,
            table_label=table_label,
            instance=instance,
            extra_mandatory_fields=extra_mandatory_fields,
            prohibited_fields=prohibited_fields,
            unique_valued_fields=unique_valued_fields,
            fixed_config=fixed_config,
            check_record_created=check_record_created,
        )
        # Maximum number of fields to fill (except if mandatory is more)
        self.min_fields = min_fields
        self.max_fields = 999999999 if max_fields is None else max_fields
        self.page_on_form_view = (
            False  # Indicates if the page is on the form view; used in validation
        )

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get the task configuration
        assert self.all_configs is not None, "No configuration available for the task."
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        # If fixed_config is not None we already set the required attributes in the constructor
        if self.fixed_config is None:
            self._set_required_config_attributes(config)
        self.protected_fields = self.task_fields
        # Generate the goal
        goal = (
            f"Create a new {self.table_label} with "
            + prettyprint_enum(
                [
                    f'a value of "{self.template_record[f]}"'
                    + f' for field "{config["fields"][f]}"'
                    for f in self.task_fields
                ]
            )
            + "."
        )
        info = {}

        return goal, info

    def _generate_random_config(self, page: Page) -> None:
        """Generate a random configuration for the task."""
        self.setup(page=page)

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
            new_value = self.get_new_field_value(f, self.template_record, self.table_metadata)
            self.template_record[f] = new_value

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

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        class_name = self.__class__.__name__
        class_name = class_name.replace("Create", "").replace("Task", "")

        # Split the words
        words = re.findall(r"[A-Z][^A-Z]*", class_name)
        class_name_formatted = " ".join(words)
        table_metadata = table_column_info(instance=self.instance, table=self.table_name)
        # pretty field names that are displayed to the user
        task_fields = []
        for field in self.task_fields:
            # In feasible tasks, the fields are always present
            if field in table_metadata:
                field_name = table_metadata[field]["label"]
            # In infeasible tasks, the fields are absent from table_metadata
            else:
                field_name = " ".join(field.split("_")).capitalize()

            task_fields.append(field_name)

        field_values = [self.template_record[field] for field in self.task_fields]
        current_task_info = dict(zip(task_fields, field_values))
        task_info = f"- Create a {class_name_formatted} with the following information: \n"
        for field, value in current_task_info.items():
            task_info += f"    - {field}: {value} \n"

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
        # If we are on the list view of the table, click on the "New" button
        self._wait_for_ready(page, iframe_only=True)
        iframe = page.frame_locator(f'iframe[name="{self.js_prefix}"]')
        url = parse.urlparse(parse.unquote(self.page.evaluate("() => window.location.href")))
        if url.path.endswith("_list.do"):
            # click on the sysverb_new button
            with page.expect_navigation():
                iframe.locator("#sysverb_new").click()
                iframe = page.frame_locator(f'iframe[name="{self.js_prefix}"]')
                # On the change request page, additional steps need to be taken to open the form
                if self.table_label == "change request":
                    self._wait_for_ready(page, iframe_only=True)
                    iframe.get_by_label("All").click()
                    iframe.get_by_text("Normal").first.click()
        self._fill_fields(page, iframe, self.task_fields)

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

        right_url = self._page_on_right_url(page)
        if not right_url:
            return (
                0,
                False,
                "",
                {
                    "message": f"The page is not in the right URL to validate task {self.__class__.__name__}."
                },
            )
        protected_field_changed = page.evaluate(
            "() => window.gsft_main.WORKARENA_BAD_FIELD_CHANGED"
        )
        if protected_field_changed:
            return (
                0,
                True,
                "",
                {"message": "Some fields outside of the task scope have been changed."},
            )
        if self.table_metadata is None and self.page_is_form_view:
            # XXX We need to ensure the table metadata as well as fields are set
            # before we can proceed with the cheat function
            self._wait_for_ready(page, iframe_only=True)
            self._get_form(page)
        if self.fields is None and self.page_is_form_view:
            self._get_fields(page)

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
            if record[f] != self.template_record[f]:
                logging.info(
                    f'The field "{self.fields[f]["label"]}" has the wrong value. Expected: "{self.template_record[f]}", got: "{record[f]}".'
                )
                error_msg = f'The field "{self.fields[f]["label"]}" has the wrong value.'
                return (
                    0,
                    True,  # End episode (incorrect information pushed to the DB)
                    error_msg,
                    {"message": error_msg},
                )

        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The record was successfully created."},
        )

    def _page_on_right_url(self, page: Page) -> bool:
        """Checks if the page is on the right URL for validation + sets the page_on_form_view attribute"""
        page.wait_for_load_state("domcontentloaded")
        self._wait_for_ready(page, iframe_only=True)
        # check that the page is at the right url
        list_url = self.start_url.replace(".do", "_list.do")  # list view of records
        # Check whether we are in the form or list view
        self.page_is_form_view = check_url_suffix_match(
            page, expected_url=self.start_url, task=self
        )
        page_is_list_view = check_url_suffix_match(page, expected_url=list_url, task=self)

        right_url = self.page_is_form_view or page_is_list_view

        return right_url

    def teardown(self) -> None:
        self._wait_for_ready(self.page, iframe_only=True)

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


class EditRecordTask(ServiceNowFormTask, CompositionalBuildingBlockTask):
    """
    Generic task to edit an existing record in a table using a Glide form.
    Class Attributes
    ----------------
    config_path: str
        The path to the JSON file containing all configurations for the task. Defined by subclasses
    expected_fields_path: str
        The path to the JSON file containing all expected fields for the task. Defined by subclasses
    Args
    ----
    form_url: str
        The URL of the form to use to edit the record.
    table_label: str
        The pretty-printed name of the table.
    instance: SNowInstance
        The instance on which to edit the record.
    extra_mandatory_fields: List
        List of fields that should be marked as mandatory in the form (overrides the page specification).
    prohibited_fields: List
        List of fields that should not be edited.
    unique_valued_fields: dict
        Dictionary of fields that should have a unique value. Keys are the field names and values are functions
        used to make the fields unique (e.g., appending self.unique).
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        a randomly selected one
    record_sys_id: str
        The sys_id of the record to edit. If provided, the task will edit this record instead of creating a new one.
    record_number: str
        The number of the record to edit. If provided, the task's cheat will select records based on it rather than picking the first element of the list.
    new_values: dict
        Dictionary mapping fields to their new values. These are values that will be used to either replace the current
        values in the record or add them to the record if they are not already present.
    """

    def __init__(
        self,
        form_url: str,
        table_label: str,
        instance: SNowInstance = None,
        extra_mandatory_fields: List = [],
        prohibited_fields: List = [],
        unique_valued_fields: dict = {},
        fixed_config: dict = None,
        record_sys_id: str = None,
        record_number: str = None,
        new_values: dict = None,
        seed: int = None,
    ) -> None:
        super().__init__(
            seed=seed,
            form_url=form_url,
            table_label=table_label,
            instance=instance,
            extra_mandatory_fields=extra_mandatory_fields,
            prohibited_fields=prohibited_fields,
            unique_valued_fields=unique_valued_fields,
            fixed_config=fixed_config,
        )
        # sys_id of the record that will be edited
        self.record_sys_id = record_sys_id
        self.record_number = record_number
        self.delete_record_on_teardown = False
        self.new_values = new_values  # dict mapping fields to their new values
        # If the record sys_id is provided, the task will fetch its template record and task fields
        if self.record_sys_id is not None:
            fixed_config = {}
            template_record = table_api_call(
                instance=self.instance,
                table=self.table_name,
                params={
                    "sysparm_query": f"sys_id={self.record_sys_id}",
                },
            )["result"][0]
            fixed_config["template_record"] = template_record
            fixed_config["task_fields"] = list(self.new_values.keys())
            table_info = table_column_info(instance=self.instance, table=self.table_name)
            fixed_config["fields"] = {f: table_info[f]["label"] for f in self.new_values.keys()}

            self.fixed_config = fixed_config

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get the task configuration
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)

        # If fixed_config is not None we already set the required attributes in the constructor
        # If record_sys_id is not None, the required attributes are not set in the constructor either
        if self.fixed_config is None or self.record_sys_id is not None:
            self._set_required_config_attributes(config)

            # Make the new values unique if needed
            for f, func in self.unique_valued_fields.items():
                if f in self.new_values:
                    self.new_values[f] = func(self.new_values[f])

        self.protected_fields = list(self.new_values.keys())
        if self.record_sys_id is None:
            self._create_record()
            self.delete_record_on_teardown = True
        # Replace the values in the template record
        for f, v in self.new_values.items():
            self.template_record[f] = v
        self.start_url = f"{self.start_url}%3Fsys_id%3D{self.record_sys_id}"

        # Generate the goal
        goal = self.get_pretty_printed_description()

        info = {}

        return goal, info

    def _create_record(self) -> None:
        """Create a record to edit."""
        # Data to create the record
        data = {}
        for field in self.template_record:
            value = self.template_record[field]
            if type(value) == dict:
                value = value["display_value"]
            # Skip sys fields as they are not editable
            if not value or "sys" in field:
                continue
            data[field] = value

        result = table_api_call(
            instance=self.instance,
            table=self.table_name,
            data=json.dumps(data),
            method="POST",
        )
        self.record_sys_id = result["result"]["sys_id"]

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        class_name = self.__class__.__name__
        class_name = class_name.replace("Edit", "").replace("Task", "")
        # Split the words
        words = re.findall(r"[A-Z][^A-Z]*", class_name)
        table_metadata = table_column_info(instance=self.instance, table=self.table_name)
        task_fields = [
            table_metadata[field]["label"] for field in self.new_values
        ]  # pretty field names that are displayed to the user
        field_values = [self.template_record[field] for field in self.new_values]
        current_task_info = dict(zip(task_fields, field_values))
        # In L3, this is part of an enumeration
        task_info = "- " if self.level == 3 else ""

        task_info += (
            f"Edit the {self.table_label} record by replacing the value of "
            + prettyprint_enum(
                [
                    f' field "{field}"' + f' with value "{value}"'
                    for field, value in current_task_info.items()
                ]
            )
            + "."
        )

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
        self._wait_for_ready(page, iframe_only=True)
        iframe = page.frame_locator(f'iframe[name="{self.js_prefix}"]')
        url = parse.urlparse(parse.unquote(self.page.evaluate("() => window.location.href")))

        # Open the record preview, then the record
        if url.path.endswith("_list.do"):
            # If the record number is provided, click on the record with that number
            if self.record_number:
                iframe.locator(f"[aria-label='Preview record: {self.record_number}']").click()
            # ....otherwise, click on the first record
            else:
                iframe.locator("td").get_by_role("button").first.click()
            page.wait_for_timeout(500)

            iframe.get_by_text("Open Record").click()
            page.wait_for_function(
                "typeof window.gsft_main !== 'undefined' && window.gsft_main.WORKARENA_LOAD_COMPLETE"
            )
        page.wait_for_timeout(1000)
        self._fill_fields(page, iframe, self.new_values.keys(), update=True)

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
        page.wait_for_load_state("domcontentloaded")
        # check that the page is at the right url
        list_url = self.start_url.replace(".do", "_list.do")  # list view of records
        # Check whether we are in the form or list view
        page_is_form_view = check_url_suffix_match(page, expected_url=self.start_url, task=self)
        page_is_list_view = check_url_suffix_match(page, expected_url=list_url, task=self)
        right_url = page_is_form_view or page_is_list_view
        if not right_url:
            return (
                0,
                False,
                "",
                {
                    "message": f"The page is not in the right URL to validate task {self.__class__.__name__}."
                },
            )
        self._wait_for_ready(page, iframe_only=True)
        protected_field_changed = page.evaluate(
            "() => window.gsft_main.WORKARENA_BAD_FIELD_CHANGED"
        )
        if protected_field_changed:
            return (
                0,
                True,
                "",
                {"message": "Some fields outside of the task scope have been changed."},
            )
        if self.table_metadata is None:
            # XXX We need to ensure the table metadata as well as fields are set
            # before we can proceed with the cheat function
            self._wait_for_ready(page, iframe_only=True)
            self._get_form(page)
        if self.fields is None and page_is_form_view:
            self._get_fields(page)

        # Pull the record from the database
        record = table_api_call(
            instance=self.instance,
            table=self.table_name,
            params={
                "sysparm_query": f"sys_id={self.record_sys_id}",
                "sysparm_display_value": True,
            },
            wait_for_record=True,
        )["result"]

        # This can happen if the form was submitted but was rejected due to invalid inputs (e.g., missing mandatory fields)
        if len(record) == 0:
            logging.info(
                "The record was not found in the database. Perhaps it was deleted."
                + self.record_sys_id,
            )
            return (
                0,
                True,
                "",
                {"message": "The record was not found in the database. Perhaps it was deleted."},
            )

        # Extract display values for reference fields
        record = {
            f: v if not isinstance(v, dict) else v["display_value"] for f, v in record[0].items()
        }

        # Check that the record matches the expected values
        for f in self.new_values.keys():
            if "sys_" in f:
                continue
            if record[f] != self.template_record[f]:
                logging.info(
                    f'The field "{self.table_metadata[f]["label"]}" has the wrong value. Expected: "{self.template_record[f]}", got: "{record[f]}".'
                )
                error_msg = f'The field "{self.table_metadata[f]["label"]}" has the wrong value.'
                return (
                    0,
                    False,
                    error_msg,
                    {"message": error_msg},
                )

        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "The record was successfully edited."},
        )

    def teardown(self) -> None:
        # Delete the record created for the task
        if self.delete_record_on_teardown:
            db_delete_from_table(
                instance=self.instance, sys_id=self.record_sys_id, table=self.table_name
            )


class CreateChangeRequestTask(GenericNewRecordTask):
    """
    Task to create a new change request in the system.

    """

    config_path = CREATE_CHANGE_REQUEST_CONFIG_PATH
    expected_fields_path = EXPECTED_CHANGE_REQUEST_FORM_FIELDS_PATH

    def __init__(
        self, seed: int = None, instance=None, fixed_config: dict = None, **kwargs
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/change_request.do",
            table_label="change request",
            prohibited_fields=["chg_model", "state"],
            fixed_config=fixed_config,
        )
        self.__dict__.update(kwargs)

    def _page_on_right_url(self, page: playwright.sync_api.Page) -> bool:
        """
        The change request form lands in a view different from the list view. We need to check for this as well.
        """
        right_url = super()._page_on_right_url(page)
        # Change request creation leads to a different page when in comp task; we need to check this case as well
        change_request_landing_page = "/now/nav/ui/classic/params/target/sn_chg_model_ui_landing.do"
        page_is_change_landing = (
            check_url_suffix_match(page, expected_url=change_request_landing_page, task=self)
            if self.table_label == "change request"
            else False
        )

        right_url = right_url or page_is_change_landing

        return right_url


class CreateIncidentTask(GenericNewRecordTask):
    """
    Task to create a new incident in the system.
    """

    config_path = CREATE_INCIDENT_CONFIG_PATH
    expected_fields_path = EXPECTED_INCIDENT_FORM_FIELDS_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        check_record_created=True,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/incident.do",
            table_label="incident",
            prohibited_fields=["state"],
            fixed_config=fixed_config,
            check_record_created=check_record_created,
        )
        self.__dict__.update(kwargs)


class CreateHardwareAssetTask(GenericNewRecordTask):
    """
    Task to create a new user in the system.

    """

    config_path = CREATE_HARDWARE_CONFIG_PATH
    expected_fields_path = EXPECTED_HARDWARE_FORM_FIELDS_PATH

    def __init__(
        self, seed: int = None, instance=None, fixed_config: dict = None, **kwargs
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/alm_hardware.do",
            table_label="hardware asset",
            prohibited_fields=["install_status"],
            extra_mandatory_fields=[
                "model",
                "model_category",
                "serial_number",
                "vendor",
            ],
            unique_valued_fields={"serial_number": lambda x: f"SN-{self.unique_id}"},
            fixed_config=fixed_config,
        )
        self.__dict__.update(kwargs)


class CreateProblemTask(GenericNewRecordTask):
    """
    Task to create a new problem in the system.

    """

    config_path = CREATE_PROBLEM_CONFIG_PATH
    expected_fields_path = EXPECTED_PROBLEM_FORM_FIELDS_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        check_record_created=True,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/problem.do",
            table_label="problem",
            prohibited_fields=["state", "first_reported_by_task"],
            fixed_config=fixed_config,
            check_record_created=check_record_created,
            # TODO: The last field is disabled because somehow the value is not in the autocomplete
            #       list even though it's in the database. I'm not sure why. It doesn't matter much
            #       since in the future we'll pre-generate tasks and keep only the ones where the
            #       cheat function works.
        )
        self.__dict__.update(kwargs)


class CreateUserTask(GenericNewRecordTask):
    """
    Task to create a new user in the system.

    """

    config_path = CREATE_USER_CONFIG_PATH
    expected_fields_path = EXPECTED_USER_FORM_FIELDS_PATH

    def __init__(
        self, seed: int = None, instance=None, fixed_config: dict = None, **kwargs
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/sys_user.do",
            table_label="user",
            extra_mandatory_fields=["user_name", "first_name", "last_name", "email"],
            # XXX We use an OrderedDict to ensure that the fields are filled in the right order as the email requires the first and last name
            unique_valued_fields=OrderedDict(
                [
                    ("first_name", lambda x: fake.first_name() + "-" + fake.first_name()),
                    ("last_name", lambda x: fake.last_name() + "-" + fake.last_name()),
                    ("user_name", lambda x: str(abs(hash(x + self.unique_id)))),
                    (
                        "email",
                        lambda x: self.template_record["first_name"].lower()
                        + "."
                        + self.template_record["last_name"].lower()
                        + "@workarena.com",
                    ),
                ]
            ),
            fixed_config=fixed_config,
        )
        self.__dict__.update(kwargs)


class EditHardwareAssetTask(EditRecordTask):
    """
    Task to create a new user in the system.

    """

    config_path = CREATE_HARDWARE_CONFIG_PATH
    expected_fields_path = EXPECTED_HARDWARE_FORM_FIELDS_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        record_sys_id: str = None,
        new_values: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/alm_hardware.do",
            table_label="hardware asset",
            prohibited_fields=["install_status"],
            unique_valued_fields={"serial_number": lambda x: f"SN-{self.unique_id}"},
            new_values=new_values,
            fixed_config=fixed_config,
            record_sys_id=record_sys_id,
        )
        if self.new_values is None:
            self.new_values = {"department": "Finance"}
        self.__dict__.update(kwargs)


class EditProblemTask(EditRecordTask):
    """
    Task to edit a problem in the system.

    """

    expected_fields_path = EXPECTED_PROBLEM_FORM_FIELDS_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        new_values: dict = None,
        record_sys_id: str = None,
        record_number: str = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/problem.do",
            table_label="problem",
            prohibited_fields=["state", "first_reported_by_task"],
            new_values=new_values,
            fixed_config=fixed_config,
            record_sys_id=record_sys_id,
            record_number=record_number,
        )
        if self.new_values is None:
            self.new_values = {"assigned_to": ""}
        self.__dict__.update(kwargs)

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        if self.level == 2:
            description = "Re-assign a lowest priority problem from the user with the most assigned problems to the user with the least assigned problems."
            return description
        else:
            return ""


class EditChangeRequestScheduleTask(EditRecordTask):
    """Task to edit an existing change request's empty schedule (start and end dates)."""

    expected_fields_path = EXPECTED_CHANGE_REQUEST_FORM_FIELDS_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        new_values: dict = None,
        record_sys_id: str = None,
        skip_description: bool = False,
        goal_type: str = "base",
        level: int = 2,
        **kwargs,
    ) -> None:
        """
        args:
        -----
        skip_description: bool
            Whether to skip the description field in the change request. Used in comp tasks when this class is used multiple times.
        goal_type: str
            Choice of "base", "priority", "tight", "tight priority". The type of goal to generate. Used in compositional tasks.
        level: int
            The level of the compositional task. Used in compositional tasks.
        """
        super().__init__(
            seed=seed,
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/change_request.do",
            table_label="change request",
            prohibited_fields=["chg_model", "state"],
            new_values=new_values,
            fixed_config=fixed_config,
            record_sys_id=record_sys_id,
        )
        self.skip_description = skip_description
        self.goal_type = goal_type
        self.level = level
        self.__dict__.update(kwargs)

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in compositional tasks.
        """
        if self.skip_description or self.level == 3:
            return ""
        elif self.goal_type == "base":
            task_info = "Edit the schedule of the change requests by setting the start and end dates so that the change requests do not overlap. There should not be more than one day between conescutive change requests in the schedule."
        elif self.goal_type == "priority":
            task_info = "Edit the schedule of the change requests by setting the start and end dates so that the change requests do not overlap. There should not be more than one day between conescutive change requests in the schedule and the higher impact change requests should be tackled first."
        elif self.goal_type == "tight":
            task_info = "Edit the schedule of the change requests by setting the start and end dates so that the change requests do not overlap. There should not be more than one hour between conescutive change requests in the schedule."
        elif self.goal_type == "tight priority":
            task_info = "Edit the schedule of the change requests by setting the start and end dates so that the change requests do not overlap. There should not be more than one hour between conescutive change requests in the schedule and the higher impact change requests should be tackled first."

        task_info += " Finally, all change requests must respect the desired durations, which are determined by the risk level:\n"
        task_info += " - High risk: 3 days \n"
        task_info += " - Moderate risk: 2 days \n"
        task_info += " - Low risk: 1 day \n"

        return task_info


class EditIncidentTask(EditRecordTask):
    """
    Task to edit a new incident in the system.

    """

    expected_fields_path = EXPECTED_INCIDENT_FORM_FIELDS_PATH

    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
        new_values: dict = None,
        record_sys_id: str = None,
        **kwargs,
    ) -> None:
        super().__init__(
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/incident.do",
            table_label="incident",
            prohibited_fields=["state"],
            fixed_config=fixed_config,
            new_values=new_values,
            record_sys_id=record_sys_id,
        )
        if self.new_values is None:
            self.new_values = {"assigned_to": "fred.luddy"}
        self.__dict__.update(kwargs)


class CreateItemRequestTask(GenericNewRecordTask, CompositionalBuildingBlockTask):
    """
    Task to create a new item request in the system.
    """

    expected_fields_path = EXPECTED_REQUEST_ITEM_FORM_FIELDS_PATH

    def __init__(
        self, instance=None, fixed_config: dict = None, check_record_created=True, **kwargs
    ) -> None:
        super().__init__(
            instance=instance,
            form_url="/now/nav/ui/classic/params/target/sc_req_item.do",
            table_label="sc_req_item",
            fixed_config=fixed_config,
            check_record_created=check_record_created,
        )
        self.__dict__.update(kwargs)


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if inspect.isclass(var)
    and not issubclass(var, CompositionalBuildingBlockTask)
    and issubclass(var, ServiceNowFormTask)
    and var is not GenericNewRecordTask
    and var is not ServiceNowFormTask
]
