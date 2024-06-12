"""
Tasks related to lists

"""

import itertools
import json
import logging
import playwright.sync_api
import re

from playwright.sync_api import Page
from tenacity import retry, retry_if_exception_type, stop_after_delay
from typing import List, Tuple
from urllib import parse
from warnings import warn

from .comp_building_block import CompositionalBuildingBlockTask

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
    # EXPECTED FIELDS
    EXPECTED_ASSET_LIST_COLUMNS_PATH,
    EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
    EXPECTED_HARDWARE_COLUMNS_PATH,
    EXPECTED_INCIDENT_COLUMNS_PATH,
    EXPECTED_PROBLEM_COLUMNS_PATH,
    EXPECTED_SERVICE_CATALOG_COLUMNS_PATH,
    EXPECTED_USER_COLUMNS_PATH,
)
from .base import AbstractServiceNowTask
from .utils.form import fill_text
from .utils.utils import check_url_suffix_match


LISTS = {
    "alm_asset": {
        "url": "/now/nav/ui/classic/params/target/alm_asset_list.do",
        "forbidden_fields": ["sys_class_name"],
    },
    "alm_hardware": {
        "url": "/now/nav/ui/classic/params/target/alm_hardware_list.do",
        "forbidden_fields": [],
    },
    "change_request": {
        "url": "/now/nav/ui/classic/params/target/change_request_list.do",
        "forbidden_fields": [],
    },
    "incident": {
        "url": "/now/nav/ui/classic/params/target/incident_list.do",
        "forbidden_fields": [],
    },
    "sys_user": {
        "url": "/now/nav/ui/classic/params/target/sys_user_list.do",
        "forbidden_fields": [
            "sys_class_name",
            "roles",
            "sys_tags",
            "user_password",
            "password_needs_reset",
        ],
    },
    "sc_cat_item": {
        "url": "/now/nav/ui/classic/params/target/sc_cat_item_list.do",
        "forbidden_fields": ["roles", "sc_catalogs"],
    },
}

EXTRACT_USER_LIST_INFO_CONFIG = [
    {
        "start_rel_url": "/now/nav/ui/classic/params/target/sys_user_list.do%3Fsysparm_query%3Dactive%253Dtrue%255Ecompany%253D81fd65ecac1d55eb42a426568fc87a63%255Eemail%253Dlucius.bagnoli%40example.com%26sysparm_first_row%3D1%26sysparm_view%3D",
        "fields": {
            "user_name": "User ID",
            "email": "Email",
            "first_name": "First name",
            "last_name": "Last name",
        },
        "expected_values": [
            {
                "user_name": "lucius.bagnoli",
                "email": "lucius.bagnoli@example.com",
                "first_name": "Lucius",
                "last_name": "Bagnoli",
            }
        ],
    }
]


class ServiceNowListTask(AbstractServiceNowTask):

    @classmethod
    def all_configs(cls) -> List[dict]:
        with open(cls.config_path, "r") as f:
            return json.load(f)

    def get_init_scripts(self) -> List[str]:
        return super().get_init_scripts() + ["registerGsftMainLoaded();"]

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
        list_info["columns"] = table_column_info(
            instance=self.instance,
            table=list_info["glide_table"],
        )

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


class SortListTask(ServiceNowListTask):
    """
    Sort a list according to a column. Works with any list.

    Parameters:
    -----------
    seed: int
        Random seed
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
    expected_fields_path:
        The path to the JSON file containing all expected fields for the task. Provided by subclasses
    """

    def __init__(
        self,
        seed: int = None,
        instance=None,
        list_url="",
        forbidden_fields=[],
        fixed_config: dict = None,
        expected_fields_path: str = None,
        **kwargs,
    ) -> None:
        super().__init__(seed=seed, instance=instance, start_rel_url=list_url)
        self.min_sort_len = 1
        self.max_sort_len = 3
        self.forbidden_fields = forbidden_fields
        self.fixed_config = fixed_config
        self.config = None
        if hasattr(self, "config_path"):
            self.all_configs = self.all_configs()

        with open(expected_fields_path, "r") as f:
            self.expected_fields = set(json.load(f))
        self.list_info = None
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get the task configuration
        self.config = (
            self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        )
        self.sort_fields = self.config["sort_fields"]
        self.sort_dirs = self.config["sort_dirs"]

        # Get the task goal
        goal = self.config["goal"]
        info = {}

        return goal, info

    def start(self, page: Page) -> None:
        super().start(page)
        self._wait_for_ready(page)

        # Ensure that the fields that need to be sorted are visible (task feasibility check)
        self.list_info = self._extract_list_info(page)

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        return self.config["goal"] + "\n"

    def _generate_all_configs(self, seed: int, page: Page, n_fields_to_sort: int):
        self.setup(seed=seed, page=page)
        self._wait_for_ready(page)
        list_info = self._extract_list_info(page)

        # Get available fields
        available_fields = list(list_info["columns"].keys())
        # ... remove forbidden fields
        available_fields = [f for f in available_fields if f not in self.forbidden_fields]

        field_txt = {k: x["label"] for k, x in list_info["columns"].items()}
        dir_txt = {"asc": "ascending", "desc": "descending"}

        # compute all field combinations
        all_sort_fields = list(itertools.combinations(available_fields, n_fields_to_sort))
        # compute all direction combinations
        all_sort_dirs = list(itertools.product(*[["asc", "desc"] for _ in range(n_fields_to_sort)]))

        # product of field combinations x direction combinations
        all_configs = list(itertools.product(all_sort_fields, all_sort_dirs))

        all_configs = [
            {
                "sort_fields": sort_fields,
                "sort_dirs": sort_dirs,
                "goal": f'Sort the "{list_info["title"]}" list by the following fields:\n'
                + "\n".join(
                    [
                        f" - {field_txt[field]} ({dir_txt[dir]})"
                        for field, dir in zip(sort_fields, sort_dirs)
                    ]
                ),
            }
            for sort_fields, sort_dirs in all_configs
        ]

        return all_configs

    def _generate_random_config(self, page: Page):
        self.setup(page=page)
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
            _, done, _, _ = self.validate(page, [])
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
        super().cheat(page=page, chat_messages=chat_messages)
        self._wait_for_ready(page)
        if self.list_info is None:
            self.list_info = self._extract_list_info(page)

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
        right_url = check_url_suffix_match(
            page, expected_url=self.start_url[: self.start_url.find("%3F")], task=self
        )
        if not right_url:
            return (
                0,
                False,
                "",
                {
                    "message": f"The page is not in the right URL to validate task {self.__class__.__name__}."
                },
            )
        self._wait_for_ready(page)
        if len(self.sort_fields) == 1:
            # XXX: Treat this as a separate case because the user may have sorted by clicking
            #      on the column header. In that case, the URL will not contain the ORDERBY.
            # ... retrieve list
            list_info = self._extract_list_info(page)
            # ... get sorting info
            sort_by = page.evaluate(f'{list_info["js_selector"]}.getOrderBy()')
            sort_dir = page.evaluate(f'{list_info["js_selector"]}.sortDir')
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
            page_url = parse.unquote(page_url)
            page_query = parse.urlparse(page_url).query
            page_qs = parse.parse_qs(page_query)

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
    expected_fields_path:
        The path to the JSON file containing all expected fields for the task. Provided by subclasses
    """

    def __init__(
        self,
        seed: int = None,
        instance=None,
        list_url="",
        fixed_config: dict = None,
        expected_fields_path: str = None,
        **kwargs,
    ) -> None:
        self.min_filter_len = 2
        self.max_filter_len = 5
        super().__init__(seed=seed, instance=instance, start_rel_url=list_url)
        self.fixed_config = fixed_config
        self.config = None
        if hasattr(self, "config_path"):
            self.all_configs = self.all_configs()

        with open(expected_fields_path, "r") as f:
            self.expected_fields = set(json.load(f))
        self.table_name = list_url.split("/")[-1].split("_list.do")[0]
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get the task configuration
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        self.filter_columns = config["filter_columns"]
        self.filter_values = config["filter_values"]
        # Base filter configs do not have filter_operands, so we default to "is"
        self.filter_operators = config.get("filter_operators", ["is" for _ in self.filter_columns])
        self.filter_kind = config["filter_kind"]
        list_info = config.get("list_info")
        if list_info is None:
            list_info = {"columns": table_column_info(self.instance, self.table_name)}
        self.list_info = list_info
        self.filter_len = len(self.filter_columns)

        # Generate goal
        goal = self.get_pretty_printed_description(goal=True)
        info = {}

        return goal, info

    def start(self, page: Page) -> None:
        super().start(page)
        self._wait_for_ready(page)

    def get_pretty_printed_description(self, goal=False) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses

        args:
        goal: bool
            If True, return as the goal of the task (without the starting dash)
        """
        task_info = "" if goal else "- "
        task_info += (
            f"Create a filter for the list to extract all entries where:"
            + f" {'and' if self.filter_kind == 'AND' else 'or'} ".join(
                [
                    f'\n    - "{self.list_info["columns"][col]["label"]}" {filter_operator} "{val}"'
                    for col, filter_operator, val in zip(
                        self.filter_columns, self.filter_operators, self.filter_values
                    )
                ]
            )
        )

        return task_info

    def _generate_random_config(self, page: Page):
        self.setup(page=page)
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
            0, page.evaluate(f'{self.list_info["js_selector"]}.grandTotalRows')
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
        goal = (
            f"Create a filter for the list to extract all entries where "
            + f" {'and' if self.filter_kind == 'AND' else 'or'} ".join(
                [
                    f'"{self.list_info["columns"][col]["label"]}" is "{val}"'
                    for col, val in zip(self.filter_columns, self.filter_values)
                ]
            )
            + "."
        )

        return goal, {}

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
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
                page.wait_for_timeout(1000)

            # Refresh since new rows are added at each iteration
            filter_rows = iframe.locator(".filter_row")
            row = filter_rows.nth(i)

            # Choose field
            logging.debug("Choosing field " + self.filter_columns[i])
            field_selector = row.locator("select.filerTableSelect").first
            field_selector.select_option(self.filter_columns[i])

            # Select the right operator
            operator = self.filter_operators[i]
            operator_symbol = (
                row.locator("select.condOperator")
                .get_by_text(operator, exact=True)
                .get_attribute("value")
            )
            logging.debug(f"Choosing operator {operator}")
            row.locator("select.condOperator").select_option(operator_symbol)

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
        right_url = check_url_suffix_match(page, expected_url=self.start_url, task=self)
        if not right_url:
            return (
                0,
                False,
                "",
                {
                    "message": f"The page is not in the right URL to validate task {self.__class__.__name__}."
                },
            )
        self._wait_for_ready(page)

        # Retrieve the current query
        list_info = self._extract_list_info(page)
        current_query = list_info["query"]

        # Replace "new query" statements with the standard OR separator
        current_query = current_query.replace("^NQ", "^OR")

        # Validate query kind is ok
        if "^OR" in current_query:
            current_kind = "OR"
            current_sep = "^OR"
        else:
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

        # Handle filtering across multiple rows
        if len(set(current_columns)) < len(current_columns):
            if len(set(current_columns)) != 1:
                raise Exception("Filtering is only allowed across rows for the same column.")
            # Filter multiple rows with a column
            is_homogenous_filter = True
        else:
            # Current setting where we use multiple columns to filter
            is_homogenous_filter = False
        for index, (col, val) in enumerate(zip(current_columns, current_values)):
            col_info = self.list_info["columns"][col]
            # Get the column type
            if col_info["type"] == "reference" and val != "":
                # Get the reference table
                ref_table = col_info["reference"]
                ref_field = col_info["reference_attributes"]["display_field"]
                if is_homogenous_filter:
                    current_values[index] = table_api_call(
                        instance=self.instance,
                        table=ref_table,
                        params={
                            "sysparm_query": f"sys_id={val}",
                            "sysparm_fields": ref_field,
                            "sysparm_display_value": "all",
                        },
                    )["result"][0][ref_field]["display_value"]
                else:
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


class ExtractListInfoTask(ServiceNowListTask):
    """
    Extract information from some fields in a list. Works with any list.

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
    list_name: str
        Name of the list to extract information from.
    list_url: str
        url of the list to extract information from.
    unique_field_name: str
        Name of the field used as unique in the list. This field is required in configs.
    """

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        configs: str = "",
        list_name: str = "",
        list_url: str = "",
        unique_field_name: str = "",
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed, instance=instance, start_rel_url=list_url
        )  # For these tasks, the start URL is defined in the setup method, as the URL depends on the configuration
        self.fixed_config = fixed_config
        self.config = None
        self.all_configs = configs
        self.list_name = list_name
        self.table_name = ""
        self.unique_field_name = unique_field_name
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get the task configuration
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        self.fields = config["fields"]  # mapping between fields and their display names
        self.printed_field_names = {
            v: k for k, v in self.fields.items()
        }  # mapping between fields and their system names
        self.expected_values = config[
            "expected_values"
        ]  # mapping between fields and their expected values
        # This is setup here because the start_url depends on the config
        assert (
            self.unique_field_name in self.fields.keys()
        ), f"Unique field name {self.unique_field_name} not in fields."
        assert all(
            [self.unique_field_name in expected_value for expected_value in self.expected_values]
        ), f"Unique field name {self.unique_field_name} not in expected values."

        if not self.start_url or self.start_url == self.instance.snow_url:
            self.start_rel_url = config["start_rel_url"]
            self.start_url = self.instance.snow_url + self.start_rel_url
        # table_name can be passed in the constructor or extracted from the start_rel_url, located in the config
        if self.table_name is None:
            self.table_name = self.start_rel_url.split("/")[-1].split("_list.do")[0]

        goal = self.get_pretty_printed_description()
        info = {}

        return goal, info

    def start(self, page: Page) -> None:
        super().start(page)
        # TODO: We should add a check to make sure the required columns are present in the list

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks and used as goal in L1 tasks.
        called by subclasses
        """
        print_field_names = list(self.fields.values())
        print_field_names.remove(
            self.fields[self.unique_field_name]
        )  # the unique fields are the keys in the dict
        if len(print_field_names) > 1:
            fields_str = (
                '"' + '", "'.join(print_field_names[:-1]) + f'" and "{print_field_names[-1]}"'
            )
            printed_unique_field_name = self.fields[self.unique_field_name]
            task_description = (
                f"- Extract information of field(s) {fields_str} "
                + f'from the "{self.list_name}" list. Return the result as a json where keys are the values of the "{printed_unique_field_name}" field and values are mappings between the fields and the extracted information. Please provide this information in the chat.'
            )
        else:
            fields_str = print_field_names[0]
            task_description = f'- Extract information of field "{fields_str}" from the "{self.list_name}" list. Please provide this information in the chat.'

        return task_description

    def _wait_for_ready(self, page: Page) -> bool:
        """
        Waits for the main iframe to be fully loaded; over-rides the parent method as the cheat
        can be called on a filtered list on which there is no gsft_main.

        Returns True if the gsft_main is present, False otherwise.
        """
        gsft_main_present = False
        logging.debug(f"Waiting up to 3 seconds for gsft_main to be ready")
        try:
            page.wait_for_function(
                "typeof window.gsft_main !== 'undefined' && window.gsft_main.WORKARENA_LOAD_COMPLETE",
                timeout=3000,
            )
            logging.debug("Detected gsft_main ready")
            gsft_main_present = True
        except TimeoutError:
            logging.debug(
                "Timed out waiting for gsft_main to be ready; searching for GlideList API directly"
            )
            pass

        logging.debug("Waiting for Glide list API to be available")
        if gsft_main_present:
            page.wait_for_function("window.gsft_main.GlideList2 !== undefined")
        else:
            page.wait_for_function("window.GlideList2 !== undefined")

        logging.debug("Detected Glide list API ready")

        return gsft_main_present

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
        right_url = check_url_suffix_match(page, expected_url=self.start_url, task=self)
        if not right_url:
            return
        gft_main_present = self._wait_for_ready(page)
        if gft_main_present:
            main_element = page.wait_for_selector("iframe#gsft_main").content_frame()
        else:
            main_element = page

        main_element.wait_for_selector(
            f"#hdr_{self.table_name}"
        )  # Selector for the name of the columns
        # system name mapped to their order in the table
        all_column_elements = main_element.query_selector_all(f"#hdr_{self.table_name} th")
        required_fields_order = {}
        for i, element in enumerate(all_column_elements):
            if element.get_attribute("name") in self.fields:
                required_fields_order[element.get_attribute("name")] = i

        # Lines of the table
        table_lines = main_element.query_selector_all(
            f".list2_body [record_class={self.table_name}]"
        )

        # will hold the values to extract
        table_values = {}

        # Extract the values of the required fields
        for line_element in table_lines:
            line_fields = line_element.query_selector_all("td")
            line_values = {}
            for field, order in required_fields_order.items():
                printed_field_name = self.fields[field]
                line_values[printed_field_name] = line_fields[order].inner_text()
            printed_unique_value_name = self.fields[self.unique_field_name]
            unique_field_value = line_values[printed_unique_value_name]
            line_values.pop(printed_unique_value_name)
            table_values[unique_field_value] = line_values

        # Add the "extracted" answer to the chat messages
        if len(self.fields) > 2:
            chat_messages.append({"role": "assistant", "message": json.dumps(table_values)})
        # In this case, we expect only one field to be extracted
        else:
            expected_field = list(self.fields.keys() - {self.unique_field_name})[0]
            pretty_field_name = self.fields[expected_field]
            # Here we assume that unique_field_value is unique in the table_values
            chat_messages.append(
                {
                    "role": "assistant",
                    "message": str(table_values[unique_field_value][pretty_field_name]),
                }
            )

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        """
        Validate the solution

        Note: current implementation is limited to AND and OR filters (single type per filter) with equality operators

        """
        if (
            len(chat_messages) == 0
            or chat_messages[-1]["role"] != "assistant"
            or not chat_messages[-1]["message"]
        ):
            return 0, False, "", {"message": "No extracted values found."}

        # When 2 or more fields (unique field is always present so at least 2 fields are present), we expect a dict
        # Otherwise, we only look for the presence of the expected value in the message sent by the agent
        if len(self.fields) > 2:
            answer = json.loads(chat_messages[-1]["message"])
            for expected_line in self.expected_values:
                # Check if the line is in the visible lines
                if expected_line[self.unique_field_name] not in answer:
                    return (
                        0,
                        False,
                        "",
                        {
                            "message": f"Value {expected_line[self.unique_field_name]} for unique field {self.unique_field_name} not found in the list."
                        },
                    )
                # Check if the values are correct
                unique_value = expected_line[self.unique_field_name]
                # This checks all fields inside the dict for the unique value
                for field, value in expected_line.items():
                    # The unique field's presence is implicitly validated by the above check
                    if field == self.unique_field_name:
                        continue
                    printed_field_name = self.fields[field]
                    if answer[unique_value][printed_field_name] != value:
                        return 0, False, "", {"message": "Incorrect value."}
        # In this case, we expect only one field to be extracted
        else:
            # get the field that is not the unique field
            field = list(self.fields.keys() - {self.unique_field_name})[0]
            expected_value = str(self.expected_values[0][field])
            if expected_value not in chat_messages[-1]["message"]:
                return 0, False, "", {"message": "Incorrect value."}

        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "Correct information extracted."},
        )


class FilterAssetListTask(FilterListTask):
    config_path = FILTER_ASSET_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["alm_asset"]["url"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_ASSET_LIST_COLUMNS_PATH,
            **kwargs,
        )


class FilterChangeRequestListTask(FilterListTask):
    config_path = FILTER_CHANGE_REQUEST_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["change_request"]["url"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
            **kwargs,
        )


class FilterHardwareListTask(FilterListTask):
    config_path = FILTER_HARDWARE_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["alm_hardware"]["url"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_HARDWARE_COLUMNS_PATH,
            **kwargs,
        )


class FilterIncidentListTask(FilterListTask):
    config_path = FILTER_INCIDENT_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["incident"]["url"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_INCIDENT_COLUMNS_PATH,
            **kwargs,
        )


class FilterProblemListForWorkLoadBalancingTask(FilterListTask, CompositionalBuildingBlockTask):
    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url="/now/nav/ui/classic/params/target/problem_list.do",
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_PROBLEM_COLUMNS_PATH,
            **kwargs,
        )

    def get_pretty_printed_description(self, goal=False) -> str:
        """Override the parent method to provide a more detailed description of the task"""

        return self.goal


class FilterServiceCatalogItemListTask(FilterListTask):
    config_path = FILTER_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["sc_cat_item"]["url"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_SERVICE_CATALOG_COLUMNS_PATH,
            **kwargs,
        )


class FilterUserListTask(FilterListTask):
    config_path = FILTER_USER_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["sys_user"]["url"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_USER_COLUMNS_PATH,
            **kwargs,
        )


class SortAssetListTask(SortListTask):
    config_path = SORT_ASSET_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["alm_asset"]["url"],
            forbidden_fields=LISTS["alm_asset"]["forbidden_fields"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_ASSET_LIST_COLUMNS_PATH,
            **kwargs,
        )


class SortChangeRequestListTask(SortListTask):
    config_path = SORT_CHANGE_REQUEST_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["change_request"]["url"],
            forbidden_fields=LISTS["change_request"]["forbidden_fields"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
            **kwargs,
        )


class SortHardwareListTask(SortListTask):
    config_path = SORT_HARDWARE_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["alm_hardware"]["url"],
            forbidden_fields=LISTS["alm_hardware"]["forbidden_fields"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_HARDWARE_COLUMNS_PATH,
            **kwargs,
        )


class SortIncidentListTask(SortListTask):
    config_path = SORT_INCIDENT_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["incident"]["url"],
            forbidden_fields=LISTS["incident"]["forbidden_fields"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_INCIDENT_COLUMNS_PATH,
            **kwargs,
        )


class SortServiceCatalogItemListTask(SortListTask):
    config_path = SORT_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["sc_cat_item"]["url"],
            forbidden_fields=LISTS["sc_cat_item"]["forbidden_fields"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_SERVICE_CATALOG_COLUMNS_PATH,
            **kwargs,
        )


class SortUserListTask(SortListTask):
    config_path = SORT_USER_LIST_CONFIG_PATH

    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            list_url=LISTS["sys_user"]["url"],
            forbidden_fields=LISTS["sys_user"]["forbidden_fields"],
            fixed_config=fixed_config,
            expected_fields_path=EXPECTED_USER_COLUMNS_PATH,
            **kwargs,
        )


class ExtractUserListInfoTask(ExtractListInfoTask, CompositionalBuildingBlockTask):
    def __init__(
        self,
        seed: int = None,
        instance=None,
        fixed_config: dict = None,
        config_path=EXTRACT_USER_LIST_INFO_CONFIG,
        list_name="User",
        unique_field_name="user_name",
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            config_path=config_path,
            list_name=list_name,
            unique_field_name=unique_field_name,
            table_name="sys_user",
            **kwargs,
        )


# Register all tasks
__TASKS__ = (
    [
        value
        for name, value in locals().items()
        if re.compile(r"^Filter\w+ListTask$").match(name)
        and not issubclass(value, CompositionalBuildingBlockTask)
    ]
    + [
        value
        for name, value in locals().items()
        if re.compile(r"^Sort\w+ListTask$").match(name)
        and not issubclass(value, CompositionalBuildingBlockTask)
    ]
    + [
        value
        for name, value in locals().items()
        if re.compile(r"^Extract\w+ListInfoTask$").match(name)
        and not issubclass(value, CompositionalBuildingBlockTask)
    ]
)
