"""
Tests that are not specific to any particular kind of task.

"""

import pytest
import json
import logging
import random

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright
from playwright.sync_api import Page, TimeoutError
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from browsergym.workarena.config import (
    # navigation tasks
    ALL_MENU_PATH,
    IMPERSONATION_CONFIG_PATH,
    # form tasks
    CREATE_CHANGE_REQUEST_CONFIG_PATH,
    CREATE_HARDWARE_CONFIG_PATH,
    CREATE_INCIDENT_CONFIG_PATH,
    CREATE_PROBLEM_CONFIG_PATH,
    CREATE_USER_CONFIG_PATH,
    # list tasks
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
    # knowledge tasks
    KB_CONFIG_PATH,
    # Service Catalog tasks
    ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH,
    ORDER_IPAD_MINI_TASK_CONFIG_PATH,
    ORDER_IPAD_PRO_TASK_CONFIG_PATH,
    ORDER_SALES_LAPTOP_TASK_CONFIG_PATH,
    ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH,
    ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
    ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH,
    ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH,
    ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH,
)
from browsergym.workarena.tasks.form import (
    CreateChangeRequestTask,
    CreateHardwareAssetTask,
    CreateIncidentTask,
    CreateProblemTask,
    CreateUserTask,
)
from browsergym.workarena.tasks.knowledge import KnowledgeBaseSearchTask
from browsergym.workarena.tasks.list import (
    FilterAssetListTask,
    FilterChangeRequestListTask,
    FilterHardwareListTask,
    FilterIncidentListTask,
    FilterServiceCatalogItemListTask,
    FilterUserListTask,
    SortAssetListTask,
    SortChangeRequestListTask,
    SortHardwareListTask,
    SortIncidentListTask,
    SortServiceCatalogItemListTask,
    SortUserListTask,
)
from browsergym.workarena.tasks.navigation import AllMenuTask, ImpersonationTask
from browsergym.workarena.tasks.service_catalog import (
    OrderDeveloperLaptopTask,
    OrderIpadMiniTask,
    OrderIpadProTask,
    OrderSalesLaptopTask,
    OrderStandardLaptopTask,
    OrderAppleWatchTask,
    OrderAppleMacBookPro15Task,
    OrderDevelopmentLaptopPCTask,
    OrderLoanerLaptopTask,
)


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
def generic_task_cheat_test(task_class, config_path, page: Page, expected_goal: str = None):
    task_config = json.load(open(config_path, "r"))[0]
    task = task_class(seed=1, fixed_config=task_config)
    goal, _ = task.setup(page=page)
    if expected_goal:
        assert goal == expected_goal
    chat_messages = []
    reward, done, message, info = task.validate(page, chat_messages)
    assert (
        isinstance(reward, (int, float))
        and type(done) == bool
        and type(message) == str
        and type(info) == dict
    )
    assert done is False and reward == 0.0
    task.cheat(page=page, chat_messages=chat_messages)
    reward, done, message, info = task.validate(page, chat_messages)
    assert done is True and reward == 1.0
    task.teardown()


# Navigation tasks
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_menu_task_from_config(page: Page):
    expected_goal = 'Navigate to the "AI Search for Next Experience > Guided Setup for Zing to AI Search Migration" module of the "AI Search" application.'
    generic_task_cheat_test(AllMenuTask, ALL_MENU_PATH, page, expected_goal=expected_goal)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_impersonation_from_config(page: Page):
    expected_goal = "Impersonate the user ATF Change Management."
    generic_task_cheat_test(
        ImpersonationTask, IMPERSONATION_CONFIG_PATH, page, expected_goal=expected_goal
    )


# Service Catalog tasks
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_developer_laptop_task_from_config(page: Page):
    generic_task_cheat_test(OrderDeveloperLaptopTask, ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_ipad_mini_task_from_config(page: Page):
    generic_task_cheat_test(OrderIpadMiniTask, ORDER_IPAD_MINI_TASK_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_ipad_pro_task_from_config(page: Page):
    generic_task_cheat_test(OrderIpadProTask, ORDER_IPAD_PRO_TASK_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_sales_laptop_task_from_config(page: Page):
    generic_task_cheat_test(OrderSalesLaptopTask, ORDER_SALES_LAPTOP_TASK_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_standard_laptop_task_from_config(page: Page):
    generic_task_cheat_test(OrderStandardLaptopTask, ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_apple_watch_task_from_config(page: Page):
    expected_goal = 'Go to the hardware store and order 1 "Apple Watch"'
    generic_task_cheat_test(
        OrderAppleWatchTask,
        ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
        page,
        expected_goal=expected_goal,
    )


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_apple_macbook_pro15_task_from_config(page: Page):
    generic_task_cheat_test(
        OrderAppleMacBookPro15Task, ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH, page
    )


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_development_laptop_pc_task_from_config(page: Page):
    generic_task_cheat_test(
        OrderDevelopmentLaptopPCTask, ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH, page
    )


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_order_loaner_laptop_task_from_config(page: Page):
    generic_task_cheat_test(OrderLoanerLaptopTask, ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH, page)


# form tasks
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_create_change_request_task_from_config(page: Page):
    generic_task_cheat_test(CreateChangeRequestTask, CREATE_CHANGE_REQUEST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_create_hardware_asset_task_from_config(page: Page):
    generic_task_cheat_test(CreateHardwareAssetTask, CREATE_HARDWARE_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_create_incident_task_from_config(page: Page):
    generic_task_cheat_test(CreateIncidentTask, CREATE_INCIDENT_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_create_problem_task_from_config(page: Page):
    expected_goal = 'Create a new problem with a value of "Request for a Blackberry" for field "Problem statement", a value of "3 - Low" for field "Impact", a value of "" for field "Service", a value of "Hardware" for field "Category", a value of "bizonal wateringly nonsuccessful checkerberry abridgeable" for field "Description", and a value of "" for field "Configuration item".'
    generic_task_cheat_test(
        CreateProblemTask, CREATE_PROBLEM_CONFIG_PATH, page, expected_goal=expected_goal
    )


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_create_user_task_from_config(page: Page):
    generic_task_cheat_test(CreateUserTask, CREATE_USER_CONFIG_PATH, page)


# knowledge tasks
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_knowledge_base_from_config(page: Page):
    expected_goal = "Answer the following question using the knowledge base: \"Can you provide the direct contact number for the CEO? Answer with the full phone number starting with the '+' sign.\""
    generic_task_cheat_test(KnowledgeBaseSearchTask, KB_CONFIG_PATH, page)


# list tasks
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_filter_asset_list_task_from_config(page: Page):
    generic_task_cheat_test(FilterAssetListTask, FILTER_ASSET_LIST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_filter_change_request_list_task_from_config(page: Page):
    expected_goal = 'Create a filter for the list to extract all entries where "Assignment group" is "Hardware" and "Assigned to" is "Bow Ruggeri".'
    generic_task_cheat_test(
        FilterChangeRequestListTask,
        FILTER_CHANGE_REQUEST_LIST_CONFIG_PATH,
        page,
        expected_goal=expected_goal,
    )


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_filter_hardware_list_task_from_config(page: Page):
    generic_task_cheat_test(FilterHardwareListTask, FILTER_HARDWARE_LIST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_filter_incident_list_task_from_config(page: Page):
    generic_task_cheat_test(FilterIncidentListTask, FILTER_INCIDENT_LIST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_filter_service_catalog_item_list_task_from_config(page: Page):
    generic_task_cheat_test(
        FilterServiceCatalogItemListTask,
        FILTER_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
        page,
    )


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_filter_user_list_task_from_config(page: Page):
    generic_task_cheat_test(FilterUserListTask, FILTER_USER_LIST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_sort_asset_list_task_from_config(page: Page):
    generic_task_cheat_test(SortAssetListTask, SORT_ASSET_LIST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_sort_change_request_list_task_from_config(page: Page):
    generic_task_cheat_test(SortChangeRequestListTask, SORT_CHANGE_REQUEST_LIST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_sort_hardware_list_task_from_config(page: Page):
    generic_task_cheat_test(SortHardwareListTask, SORT_HARDWARE_LIST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_sort_incident_list_task_from_config(page: Page):
    generic_task_cheat_test(SortIncidentListTask, SORT_INCIDENT_LIST_CONFIG_PATH, page)


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_sort_service_catalog_item_list_task_from_config(page: Page):
    generic_task_cheat_test(
        SortServiceCatalogItemListTask, SORT_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH, page
    )


@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_sort_user_list_task_from_config(page: Page):
    expected_goal = 'Sort the "users" list by the following fields:\n - Active (descending)'
    generic_task_cheat_test(
        SortUserListTask, SORT_USER_LIST_CONFIG_PATH, page, expected_goal=expected_goal
    )
