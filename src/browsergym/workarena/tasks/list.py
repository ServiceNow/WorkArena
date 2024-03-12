"""
Tasks related to lists

"""

import json
import logging
import playwright.sync_api
import re
import urllib.parse

from playwright.sync_api import Page
from tenacity import retry, retry_if_exception_type, stop_after_delay
from typing import Tuple
from warnings import warn

from ..api.utils import table_api_call, table_column_info
from ..config import (
    SNOW_BROWSER_TIMEOUT,
    FILTER_ASSET_LIST_CONFIG_PATH,
    FILTER_CHANGE_REQUEST_LIST_CONFIG_PATH,
    FILTER_HARDWARE_LIST_CONFIG_PATH,
    FILTER_INCIDENT_LIST_CONFIG_PATH,
    FILTER_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
    FILTER_USER_LIST_CONFIG_PATH,
    SORT_ASSET_LIST_CONFIG_PATH,
    SORT_CHANGE_REQUEST_LIST_CONFIG_PATH,
    SORT_HARDWARE_LIST_CONFIG_PATH,
    SORT_INCIDENT_LIST_CONFIG_PATH,
    SORT_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
    SORT_USER_LIST_CONFIG_PATH,
)
from .base import AbstractServiceNowTask
from .utils.form import fill_text


LISTS = {
    "alm_asset": {
        "url": "/now/nav/ui/classic/params/target/alm_asset_list.do%3Fsysparm_view%3Ditam_workspace%26sysparm_userpref.alm_asset_list.view%3Ditam_workspace%26sysparm_userpref.alm_asset.view%3Ditam_workspace%26sysparm_query%3D%26sysparm_fixed_query%3D",
        "forbidden_fields": ["sys_class_name"],
    },
    "alm_hardware": {
        "url": "/now/nav/ui/classic/params/target/alm_hardware_list.do%3Fsysparm_view%3Ditam_workspace%26sysparm_userpref.alm_hardware_list.view%3Ditam_workspace%26sysparm_userpref.alm_hardware.view%3Ditam_workspace%3D%26sysparm_query%3Dinstall_status%253D6%255Esubstatus%253Dpre_allocated",
        "forbidden_fields": [],
    },
    "change_request": {
        "url": "/now/nav/ui/classic/params/target/change_request_list.do%3Fsysparm_view%3Dsow%26sysparm_userpref.change_request_list.view%3Dsow%26sysparm_userpref.change_request.view%3Dsow%26sysparm_query%3D%26sysparm_fixed_query%3D",
        "forbidden_fields": [],
    },
    "incident": {
        "url": "/now/nav/ui/classic/params/target/incident_list.do%3Fsysparm_query%3Dactive%253Dtrue%26sysparm_first_row%3D1%26sysparm_view%3DMajor%2520Incidents",
        "forbidden_fields": [],
    },
    "sys_user": {
        "url": "/now/nav/ui/classic/params/target/sys_user_list.do%3Fsysparm_view%3D%26sysparm_userpref.sys_user_list.view%3D%26sysparm_userpref.sys_user.view%3D%26sysparm_query%3Dactive%253Dtrue%255Ecompany%253D81fd65ecac1d55eb42a426568fc87a63",
        "forbidden_fields": [
            "sys_class_name",
            "roles",
            "sys_tags",
            "user_password",
            "password_needs_reset",
        ],
    },
    "sc_cat_item": {
        "url": "/now/nav/ui/classic/params/target/sc_cat_item_list.do%3Fsysparm_view%3D%26sysparm_userpref.sc_cat_item_list.view%3D%26sysparm_userpref.sc_cat_item.view%3D%26sysparm_query%3D%26sysparm_fixed_query%3D",
        "forbidden_fields": ["roles", "sc_catalogs"],
    },
}


class ServiceNowListTask(AbstractServiceNowTask):
    def _get_visible_list(self, page: Page):
        self._wait_for_ready(page)

        iframe = page.frame("gsft_main")
        lst = iframe.locator("table.data_list_table")
        lst.wait_for()

        # Validate the number of lists on the page
        if lst.count() > 1:
            warn(
                "More than one list found on page. Using the first one.",
                category=RuntimeWarning,
            )
        elif lst.count() == 0:
            raise RuntimeError("No list found on page.")
        lst = lst.nth(0)

        # A javascript command that gets the list object
        javascript_selector = f"gsft_main.GlideList2.get('{lst.get_attribute('data-list_id')}')"

        return iframe, lst, javascript_selector

    @retry(
        stop=stop_after_delay(SNOW_BROWSER_TIMEOUT / 1000),
        retry=retry_if_exception_type(playwright.sync_api.Error),
        reraise=True,
        before_sleep=lambda _: logging.debug("Retrying due to a Playwright Error..."),
    )
    def _extract_list_info(self, page: Page, with_data=False):
        """
        Extract useful information about the list visible on the page

        """
        self._wait_for_ready(page)

        # Grab the list component
        _, _, js_selector = self._get_visible_list(page)

        # Load some basic info
        list_info = {
            "title": page.evaluate(f"{js_selector}.getTitle()").lower(),
            "glide_table": page.evaluate(f"{js_selector}.getTableName()").lower(),
            "query": page.evaluate(f"{js_selector}.getQuery()"),
            "fields": page.evaluate(f"{js_selector}.fields"),
            "js_selector": js_selector,
        }

        # Get column info
        fields = list_info["fields"].split(",")
        list_info["columns"] = table_column_info(
            instance=self.instance,
            table=list_info["glide_table"],
        )
        list_info["columns"] = {k: v for k, v in list_info["columns"].items() if k in fields}

        # Get the list data
        if with_data:
            data = table_api_call(
                instance=self.instance,
                table=list_info["glide_table"],
                params={
                    "sysparm_query": list_info["query"],
                    "sysparm_fields": list_info["fields"],
                    "sysparm_display_value": "all",
                },
            )["result"]
            # Extract all display values (not raw values)
            data = [{k: v["display_value"] for k, v in x.items()} for x in data]
            list_info["data"] = data

        return list_info

    def _wait_for_ready(self, page: Page) -> None:
        """
        Waits for the main iframe to be fully loaded

        """
        logging.debug(f"Waiting for gsft_main to be fully loaded")
        page.wait_for_function(
            "typeof window.gsft_main !== 'undefined' && window.gsft_main.WORKARENA_LOAD_COMPLETE"
        )
        logging.debug("Detected gsft_main ready")

        logging.debug("Waiting for Glide list API to be available")
        page.wait_for_function("window.gsft_main.GlideList2 !== undefined")
        logging.debug("Detected Glide list API ready")

    def pre_setup(self, seed: int, page: Page):
        super().pre_setup(seed, page)

        self._add_init_scripts_to_context_and_reload(
            page,
            [
                "registerGsftMainLoaded();",
            ],
        )


class SortListTask(ServiceNowListTask):
    """
    Sort a list according to a column. Works with any list.

    Parameters:
    -----------
    instance: SNowInstance
        The instance to use.
    list_url: str
        The relative URL of the list to sort.
    forbidden_fields: list[str]
        A list of fields that should not be used for sorting.
        This is used to avoid sorting by fields that are disabled
        in the UI.
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/sort_change_request_list_task.json
        for an example of a configuration file.
    config_path:
        The path to the JSON file containing all configurations for the task. Provided by subclasses
    """

    def __init__(
        self,
        instance=None,
        list_url="",
        forbidden_fields=[],
        fixed_config: dict = None,
        config_path: str = None,
    ) -> None:
        super().__init__(instance=instance, start_rel_url=list_url)
        self.min_sort_len = 1
        self.max_sort_len = 3
        self.forbidden_fields = forbidden_fields
        self.fixed_config = fixed_config
        if config_path:
            with open(config_path, "r") as f:
                self.all_configs = json.load(f)

    def setup(self, seed: int, page: Page) -> tuple[str, dict]:
        self.pre_setup(seed, page)
        self._wait_for_ready(page)
        # Extract the list from the page
        self.list_info = self._extract_list_info(page)
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)

        config = self.random.choice(self.all_configs)
        self.sort_fields = config["sort_fields"]
        self.sort_dirs = config["sort_dirs"]
        self.goal = config["goal"]

    def get_goal(self) -> str:
        return self.goal

    def _generate_random_config(self, seed: int, page: Page):
        super().setup(seed, page)
        self._wait_for_ready(page)
        self.list_info = self._extract_list_info(page)
        # Get available fields
        available_fields = list(self.list_info["columns"].keys())
        # ... remove forbidden fields
        available_fields = [f for f in available_fields if f not in self.forbidden_fields]

        sort_len = self.random.randint(
            self.min_sort_len, min(self.max_sort_len, len(available_fields)) + 1
        )

        # Pick random fields and directions to sort
        # Retry until the task is not initially solved
        try_again = True
        while try_again:
            try_again = False

            self.sort_fields = list(
                self.random.choice(available_fields, size=sort_len, replace=False)
            )
            self.sort_dirs = list(self.random.choice(["asc", "desc"], size=sort_len, replace=True))

            dir_txt = {"asc": "ascending", "desc": "descending"}

            sort_fields_txt = [
                self.list_info["columns"][sort_field]["label"] for sort_field in self.sort_fields
            ]
            sort_dirs_txt = [dir_txt[sort_dir] for sort_dir in self.sort_dirs]

            # check if the task is already solved (can happen if the chosen field is already sorted in the default view)
            _, done, _, _ = self.validate(self.page, [])
            # if so, pick new fields
            if done:
                logging.warning("Trivial config for sort list task, picking a new config.")
                try_again = True

        # generate goal
        goal = f'Sort the "{self.list_info["title"]}" list by the following fields:\n'
        goal += "\n".join(
            [f" - {field} ({dir})" for field, dir in zip(sort_fields_txt, sort_dirs_txt)]
        )
        info = {}

        return goal, info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page, chat_messages)
        self._wait_for_ready(page)

        iframe, _, _ = self._get_visible_list(page)

        iframe.locator(".list_filter_toggle").click()

        # Wait for the filter to be visible
        iframe.wait_for_function(
            "typeof document.querySelectorAll('.list_filter')[0] !== 'undefined' && document.querySelectorAll('.list_filter')[0].offsetParent !== null"
        )

        dir_txt = {"asc": "ascending", "desc": "descending"}
        sort_fields_txt = [
            self.list_info["columns"][sort_field]["label"] for sort_field in self.sort_fields
        ]
        sort_dirs_txt = [dir_txt[sort_dir] for sort_dir in self.sort_dirs]

        filter = iframe.locator(".list_filter")

        # skip filter rows, which are placed before sorting rows

        # Add all sorting conditions
        for i, (field_txt, dir_txt) in enumerate(zip(sort_fields_txt, sort_dirs_txt)):
            logging.debug(f"Adding sort condition for column {repr(field_txt)} ({dir_txt}).")
            filter.get_by_role("button", name="Add Sort").click()

            # TODO: Hack to solve bug where the sort condition has not yet appeared
            page.wait_for_timeout(500)

            # newly added row should be the last one
            row_index = filter.locator(".filter_row").count() - 1

            # Refresh since new rows are added at each iteration
            row = iframe.locator(".filter_row").nth(row_index)
            row_selectors = row.locator("select.filerTableSelect")
            field_selector = row_selectors.nth(0)
            dir_selector = row_selectors.nth(1)

            # Choose field
            logging.debug(f"Choosing sorting field {field_txt}")
            field_selector.select_option(field_txt)

            # Choose sort order
            logging.debug(f"Choosing sorting direction {dir_txt}")
            dir_selector.select_option(dir_txt)

        # hack to wait for two events
        n_events_to_wait = 2

        def n_events_passed(event_info):
            nonlocal n_events_to_wait
            n_events_to_wait -= 1
            return n_events_to_wait == 0

        # click and wait for two navigations to happen (the iframe will navigate first, the page after)
        with page.expect_event("framenavigated", predicate=n_events_passed):
            filter.get_by_label("Run filter").click()

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        self._wait_for_ready(page)

        if len(self.sort_fields) == 1:
            # XXX: Treat this as a separate case because the user may have sorted by clicking
            #      on the column header. In that case, the URL will not contain the ORDERBY.
            # ... retrieve list
            list_info = self._extract_list_info(page)
            # ... get sorting info
            sort_by = self.page.evaluate(f'{list_info["js_selector"]}.getOrderBy()')
            sort_dir = self.page.evaluate(f'{list_info["js_selector"]}.sortDir')
            # ... check if the list is sorted correctly
            if sort_by == self.sort_fields[0] and sort_dir.lower() == self.sort_dirs[0]:
                return (
                    1,
                    True,
                    "Nice work, thank you!",
                    {"message": "Correct sorting."},
                )

        else:
            # pre-process the URL
            page_url = page.evaluate("() => window.location.href")
            page_url = urllib.parse.unquote(page_url)
            page_query = urllib.parse.urlparse(page_url).query
            page_qs = urllib.parse.parse_qs(page_query)

            # make sure "sysparm_query" is present
            if "sysparm_query" not in page_qs:
                return 0, False, "", {"message": "No sysparm_query found in URL."}

            # concatenate desired order_by conditions
            order_dir = {"asc": "", "desc": "DESC"}
            sysparam_query_regex = r"\^".join(
                [
                    f"ORDERBY{order_dir[dir]}{field}"
                    for field, dir in zip(self.sort_fields, self.sort_dirs)
                ]
            )
            sysparam_query_regex = (
                r"^((?!ORDERBY).)*" + sysparam_query_regex + r"((?!ORDERBY).)*$"
            )  # forbid undesired order_by conditions

            # check "sysparm_query" for the correct sort conditions
            page_sysparam_query = page_qs["sysparm_query"][0]
            if page_sysparam_query and re.match(sysparam_query_regex, page_sysparam_query):
                return (
                    1,
                    True,
                    "Nice work, thank you!",
                    {"message": "Correct sorting."},
                )

        return 0, False, "", {"message": "Incorrect sorting."}


class FilterListTask(ServiceNowListTask):
    """
    Filter a list according to a few columns. Works with any list.

    Parameters:
    -----------
    instance: SNowInstance
        The instance to use.
    list_url: str
        The relative URL of the list to filter.
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/filter_change_request_list_task.json
        for an example of a configuration file.
    config_path:
        The path to the JSON file containing all configurations for the task. Provided by subclasses
    """

    def __init__(
        self, instance=None, list_url="", fixed_config: dict = None, config_path: str = None
    ) -> None:
        self.min_filter_len = 2
        self.max_filter_len = 5
        super().__init__(instance=instance, start_rel_url=list_url)
        self.fixed_config = fixed_config
        if config_path:
            with open(config_path, "r") as f:
                self.all_configs = json.load(f)

    def setup(self, seed: int, page: Page) -> tuple[str, dict]:
        self.pre_setup(seed, page)
        self._wait_for_ready(page)
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)

        self.filter_columns = config["filter_columns"]
        self.filter_values = config["filter_values"]
        self.filter_kind = config["filter_kind"]
        self.list_info = config["list_info"]
        self.filter_len = len(self.filter_columns)

    def _generate_random_config(self, seed: int, page: Page):
        super().setup(seed, page)
        self._wait_for_ready(page)

        # Extract the list from the page
        self.list_info = self._extract_list_info(page)

        # Choose the columns to filter on
        allowed_types = ["string", "choice", "reference", "translated_text", "boolean"]
        valid_filter_columns = [
            k for k, v in self.list_info["columns"].items() if v["type"] in allowed_types
        ]
        assert len(valid_filter_columns) > 0, "Not enough columns to filter on."
        self.filter_len = self.random.randint(
            self.min_filter_len, min(self.max_filter_len, len(valid_filter_columns)) + 1
        )
        self.filter_columns = list(
            self.random.choice(valid_filter_columns, self.filter_len, replace=False)
        )

        # Choose the filter kind
        if self.filter_len == 1:
            # If there is only one column to filter on, then the kind is always AND
            self.filter_kind = "AND"
        else:
            self.filter_kind = self.random.choice(["AND", "OR"])

        # Choose the values to filter on
        # We do this by loading a single record at random and using its values
        # This is significantly faster than loading all records and then filtering
        offset = self.random.randint(
            0, self.page.evaluate(f'{self.list_info["js_selector"]}.grandTotalRows')
        )
        data = table_api_call(
            instance=self.instance,
            table=self.list_info["glide_table"],
            params={
                "sysparm_query": self.list_info["query"],
                "sysparm_fields": ",".join(self.filter_columns),
                "sysparm_display_value": "all",
                "sysparm_limit": "1",
                "sysparm_offset": f"{offset}",
            },
        )["result"][0]
        # XXX: The use of "" as default display value is a hack, but it seems to work for now.
        self.filter_values = [
            data.get(c, {"display_value": ""})["display_value"] for c in self.filter_columns
        ]

        # Make sure we expand empty strings to their expected display value (the API fails to do this)
        for i, (col, val) in enumerate(zip(self.filter_columns, self.filter_values)):
            if self.list_info["columns"][col]["type"] == "choice" and val in [None, ""]:
                self.filter_values[i] = self.list_info["columns"][col]["choices"].get(
                    "", "-- None --"
                )
                # XXX: The use of -- None -- as default is a hack, but it seems to work for now.

        # Make sure there are no trailing spaces in the values
        self.filter_values = [v.strip() for v in self.filter_values]

        # Make sure we use only values that are available in the UI
        # (some database entries have old values that are no longer available)
        for i, (c, v) in enumerate(zip(self.filter_columns, self.filter_values)):
            if "choices" in self.list_info["columns"][c]:
                if v not in self.list_info["columns"][c]["choices"]:
                    # replace with a random choice
                    self.filter_values[i] = self.random.choice(
                        list(self.list_info["columns"][c]["choices"].values())
                    )

        # generate goal
        goal = (
            f'Create a filter for the "{self.list_info["title"].lower()}" list '
            + f"to extract all entries where "
            + f" {'and' if self.filter_kind == 'AND' else 'or'} ".join(
                [
                    f'"{self.list_info["columns"][col]["label"]}" is "{val}"'
                    for col, val in zip(self.filter_columns, self.filter_values)
                ]
            )
            + "."
        )
        info = {}

        return goal, info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page, chat_messages)
        self._wait_for_ready(page)

        iframe, _, _ = self._get_visible_list(page)

        iframe.locator(".list_filter_toggle").click()

        # Wait for the filter to be visible
        iframe.wait_for_function(
            "typeof document.querySelectorAll('.list_filter')[0] !== 'undefined' && document.querySelectorAll('.list_filter')[0].offsetParent !== null"
        )

        # Clear any existing filters
        # Use a while loop and click the first button until there are no more buttons
        while iframe.locator(".filerTableAction.deleteButton:visible").count() > 0:
            logging.debug("Clearing existing filter condition")
            iframe.locator(".filerTableAction.deleteButton:visible").nth(0).click()

        # TODO: Hack to solve issue where the filters were not all removed
        page.wait_for_timeout(3000)

        # Add all filter conditions
        for i in range(len(self.filter_columns)):
            logging.debug(
                "Adding filter condition for column "
                + self.filter_columns[i]
                + " with value "
                + self.filter_values[i]
            )

            # Add conditions in this loop so that it looks more dynamic
            if i > 0:
                logging.debug("Need to create new filter condition of type " + self.filter_kind)
                iframe.locator(
                    f'.filterToolbar .filerTableAction:text-is("{self.filter_kind}")'
                ).click()
                # TODO: Hack to solve bug where the filter condition has not yet appeared
                self.page.wait_for_timeout(1000)

            # Refresh since new rows are added at each iteration
            filter_rows = iframe.locator(".filter_row")
            row = filter_rows.nth(i)

            # Choose field
            logging.debug("Choosing field " + self.filter_columns[i])
            field_selector = row.locator("select.filerTableSelect").first
            field_selector.select_option(self.filter_columns[i])

            # Select the right operator
            logging.debug("Choosing operator =")
            row.locator("select.condOperator").select_option("=")

            # Fill in the value
            logging.debug("Filling in value " + self.filter_values[i])
            type_ = self.list_info["columns"][self.filter_columns[i]]["type"]
            if type_ in ["string", "reference", "translated_text"]:
                # expect a textbox
                logging.debug("filling in textbox")

                # If empty, don't do anything
                if self.filter_values[i] == "":
                    continue

                # Find the value input field
                inputs = row.locator("#value input")
                input_field = [
                    inputs.nth(j) for j in range(inputs.count()) if inputs.nth(j).is_visible()
                ][0]
                fill_text(
                    page=page,
                    iframe=iframe,
                    input_field=input_field,
                    value=self.filter_values[i],
                )
            else:
                # expect a selector
                logging.debug("filling in selector")
                # Find the value input field
                input_field = row.locator("#value select")
                input_field.select_option(self.filter_values[i])

        iframe.locator(".filterToolbar").get_by_text("Run").click()

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        """
        Validate the solution

        Note: current implementation is limited to AND and OR filters (single type per filter) with equality operators

        """
        self._wait_for_ready(page)

        if self.filter_kind not in ["AND", "OR"]:
            raise NotImplementedError("Only AND and OR filters are supported.")
        # Excludes AND because that's the default and its sep is ^ which matches everywhere
        query_sep = {"OR": "^NQ"}

        # Retrieve list
        list_info = self._extract_list_info(page)

        # Check if the list is filtered correctly
        current_query = list_info["query"]

        # Validate query kind is ok
        current_kind = None
        for kind in query_sep:
            if query_sep[kind] in current_query:
                current_kind = kind
                current_sep = query_sep[kind]
                break
        else:
            # If no separator is found, then the query is just assumed to be AND (it's a single condition)
            current_kind = "AND"
            current_sep = "^"

        if current_kind != self.filter_kind:
            return 0, False, "", {"message": "The kind of filter used is incorrect."}

        # Extract the query pieces for validation
        current_query = current_query.split(current_sep)

        # Validate query length is ok
        if len(current_query) != self.filter_len:
            return 0, False, "", {"message": "Incorrect number of filter conditions."}

        # Validate query columns are ok
        current_columns = [x.split("=")[0] for x in current_query]
        if set(current_columns) != set(self.filter_columns):
            return 0, False, "", {"message": "Incorrect filter columns."}

        # Validate query values are ok
        # This is the tricky part because we need to expand the values to their display values
        # We also need to handle the case where the value is a reference
        current_values = [x.split("=")[1] for x in current_query]
        for col, val in zip(current_columns, current_values):
            col_info = self.list_info["columns"][col]

            # Get the column type
            if col_info["type"] == "reference" and val != "":
                # Get the reference table
                ref_table = col_info["reference"]
                ref_field = col_info["reference_attributes"]["display_field"]
                # Get the reference display value
                current_values[current_columns.index(col)] = table_api_call(
                    instance=self.instance,
                    table=ref_table,
                    params={
                        "sysparm_query": f"sys_id={val}",
                        "sysparm_fields": ref_field,
                        "sysparm_display_value": "all",
                    },
                )["result"][0][ref_field]["display_value"]

            elif col_info["type"] == "choice":
                # Get the choice display value
                current_values[current_columns.index(col)] = self.list_info["columns"][col][
                    "choices"
                ].get(val, "-- None --")
                # XXX: The above is a hack to address a rare glitch. Sometimes, empty values are allowed in the UI
                #      but that value is not in the choices. Usually, the UI shows this as -- None -- so we use that.

        # Validate the values
        if set(current_values) != set(self.filter_values):
            return 0, False, "", {"message": "Incorrect filter values."}

        return 1, True, "Nice work, thank you!", {"message": "Correct filter."}


class FilterAssetListTask(FilterListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["alm_asset"]["url"],
            fixed_config=fixed_config,
            config_path=FILTER_ASSET_LIST_CONFIG_PATH,
        )


class FilterChangeRequestListTask(FilterListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["change_request"]["url"],
            fixed_config=fixed_config,
            config_path=FILTER_CHANGE_REQUEST_LIST_CONFIG_PATH,
        )


class FilterHardwareListTask(FilterListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["alm_hardware"]["url"],
            fixed_config=fixed_config,
            config_path=FILTER_HARDWARE_LIST_CONFIG_PATH,
        )


class FilterIncidentListTask(FilterListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["incident"]["url"],
            fixed_config=fixed_config,
            config_path=FILTER_INCIDENT_LIST_CONFIG_PATH,
        )


class FilterServiceCatalogItemListTask(FilterListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["sc_cat_item"]["url"],
            fixed_config=fixed_config,
            config_path=FILTER_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
        )


class FilterUserListTask(FilterListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["sys_user"]["url"],
            fixed_config=fixed_config,
            config_path=FILTER_USER_LIST_CONFIG_PATH,
        )


class SortAssetListTask(SortListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["alm_asset"]["url"],
            forbidden_fields=LISTS["alm_asset"]["forbidden_fields"],
            fixed_config=fixed_config,
            config_path=SORT_ASSET_LIST_CONFIG_PATH,
        )


class SortChangeRequestListTask(SortListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["change_request"]["url"],
            forbidden_fields=LISTS["change_request"]["forbidden_fields"],
            fixed_config=fixed_config,
            config_path=SORT_CHANGE_REQUEST_LIST_CONFIG_PATH,
        )


class SortHardwareListTask(SortListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["alm_hardware"]["url"],
            forbidden_fields=LISTS["alm_hardware"]["forbidden_fields"],
            fixed_config=fixed_config,
            config_path=SORT_HARDWARE_LIST_CONFIG_PATH,
        )


class SortIncidentListTask(SortListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["incident"]["url"],
            forbidden_fields=LISTS["incident"]["forbidden_fields"],
            fixed_config=fixed_config,
            config_path=SORT_INCIDENT_LIST_CONFIG_PATH,
        )


class SortServiceCatalogItemListTask(SortListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["sc_cat_item"]["url"],
            forbidden_fields=LISTS["sc_cat_item"]["forbidden_fields"],
            fixed_config=fixed_config,
            config_path=SORT_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
        )


class SortUserListTask(SortListTask):
    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
    ) -> None:
        super().__init__(
            instance,
            list_url=LISTS["sys_user"]["url"],
            forbidden_fields=LISTS["sys_user"]["forbidden_fields"],
            fixed_config=fixed_config,
            config_path=SORT_USER_LIST_CONFIG_PATH,
        )


# Register all tasks
__TASKS__ = [
    value for name, value in locals().items() if re.compile(r"^Filter\w+ListTask$").match(name)
] + [value for name, value in locals().items() if re.compile(r"^Sort\w+ListTask$").match(name)]
