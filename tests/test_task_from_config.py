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
def generic_task_cheat_test(task_class, config_path, page: Page):
    task_config = json.load(open(config_path, "r"))[0]

    task = task_class(fixed_config=task_config)
    task.setup(page=page, seed=1)
    chat_messages = []
    assert task.validate(page, chat_messages)[1] is False
    task.cheat(page=page, chat_messages=chat_messages)
    assert task.validate(page, chat_messages)[1] is True
    task.teardown()


# Navigation tasks
@pytest.mark.slow
def test_menu_task_from_config(page: Page):
    generic_task_cheat_test(AllMenuTask, ALL_MENU_PATH, page)


@pytest.mark.slow
def test_impersonation_from_config(page: Page):
    generic_task_cheat_test(ImpersonationTask, IMPERSONATION_CONFIG_PATH, page)


# Service Catalog tasks
@pytest.mark.slow
def test_order_developer_laptop_task_from_config(page: Page):
    generic_task_cheat_test(OrderDeveloperLaptopTask, ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH, page)


@pytest.mark.slow
def test_order_ipad_mini_task_from_config(page: Page):
    generic_task_cheat_test(OrderIpadMiniTask, ORDER_IPAD_MINI_TASK_CONFIG_PATH, page)


@pytest.mark.slow
def test_order_ipad_pro_task_from_config(page: Page):
    generic_task_cheat_test(OrderIpadProTask, ORDER_IPAD_PRO_TASK_CONFIG_PATH, page)


@pytest.mark.slow
def test_order_sales_laptop_task_from_config(page: Page):
    generic_task_cheat_test(OrderSalesLaptopTask, ORDER_SALES_LAPTOP_TASK_CONFIG_PATH, page)


@pytest.mark.slow
def test_order_standard_laptop_task_from_config(page: Page):
    generic_task_cheat_test(OrderStandardLaptopTask, ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH, page)


@pytest.mark.slow
def test_order_apple_watch_task_from_config(page: Page):
    generic_task_cheat_test(OrderAppleWatchTask, ORDER_APPLE_WATCH_TASK_CONFIG_PATH, page)


@pytest.mark.slow
def test_order_apple_macbook_pro15_task_from_config(page: Page):
    generic_task_cheat_test(
        OrderAppleMacBookPro15Task, ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH, page
    )


@pytest.mark.slow
def test_order_development_laptop_pc_task_from_config(page: Page):
    generic_task_cheat_test(
        OrderDevelopmentLaptopPCTask, ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH, page
    )


@pytest.mark.slow
def test_order_loaner_laptop_task_from_config(page: Page):
    generic_task_cheat_test(OrderLoanerLaptopTask, ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH, page)


# form tasks
@pytest.mark.slow
def test_create_change_request_task_from_config(page: Page):
    generic_task_cheat_test(CreateChangeRequestTask, CREATE_CHANGE_REQUEST_CONFIG_PATH, page)


@pytest.mark.slow
def test_create_hardware_asset_task_from_config(page: Page):
    generic_task_cheat_test(CreateHardwareAssetTask, CREATE_HARDWARE_CONFIG_PATH, page)


@pytest.mark.slow
def test_create_incident_task_from_config(page: Page):
    generic_task_cheat_test(CreateIncidentTask, CREATE_INCIDENT_CONFIG_PATH, page)


@pytest.mark.slow
def test_create_problem_task_from_config(page: Page):
    generic_task_cheat_test(CreateProblemTask, CREATE_PROBLEM_CONFIG_PATH, page)


@pytest.mark.slow
def test_create_user_task_from_config(page: Page):
    generic_task_cheat_test(CreateUserTask, CREATE_USER_CONFIG_PATH, page)


# knowledge tasks
@pytest.mark.slow
def test_knowledge_base_from_config(page: Page):
    generic_task_cheat_test(KnowledgeBaseSearchTask, KB_CONFIG_PATH, page)


# list tasks
@pytest.mark.slow
def test_filter_asset_list_task_from_config(page: Page):
    generic_task_cheat_test(FilterAssetListTask, FILTER_ASSET_LIST_CONFIG_PATH, page)


@pytest.mark.slow
def test_filter_change_request_list_task_from_config(page: Page):
    generic_task_cheat_test(
        FilterChangeRequestListTask, FILTER_CHANGE_REQUEST_LIST_CONFIG_PATH, page
    )


@pytest.mark.slow
def test_filter_hardware_list_task_from_config(page: Page):
    generic_task_cheat_test(FilterHardwareListTask, FILTER_HARDWARE_LIST_CONFIG_PATH, page)


@pytest.mark.slow
def test_filter_incident_list_task_from_config(page: Page):
    generic_task_cheat_test(FilterIncidentListTask, FILTER_INCIDENT_LIST_CONFIG_PATH, page)


@pytest.mark.slow
def test_filter_service_catalog_item_list_task_from_config(page: Page):
    generic_task_cheat_test(
        FilterServiceCatalogItemListTask, FILTER_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH, page
    )


@pytest.mark.slow
def test_filter_user_list_task_from_config(page: Page):
    generic_task_cheat_test(FilterUserListTask, FILTER_USER_LIST_CONFIG_PATH, page)


@pytest.mark.slow
def test_sort_asset_list_task_from_config(page: Page):
    generic_task_cheat_test(SortAssetListTask, SORT_ASSET_LIST_CONFIG_PATH, page)


@pytest.mark.slow
def test_sort_change_request_list_task_from_config(page: Page):
    generic_task_cheat_test(SortChangeRequestListTask, SORT_CHANGE_REQUEST_LIST_CONFIG_PATH, page)


@pytest.mark.slow
def test_sort_hardware_list_task_from_config(page: Page):
    generic_task_cheat_test(SortHardwareListTask, SORT_HARDWARE_LIST_CONFIG_PATH, page)


@pytest.mark.slow
def test_sort_incident_list_task_from_config(page: Page):
    generic_task_cheat_test(SortIncidentListTask, SORT_INCIDENT_LIST_CONFIG_PATH, page)


@pytest.mark.slow
def test_sort_service_catalog_item_list_task_from_config(page: Page):
    generic_task_cheat_test(
        SortServiceCatalogItemListTask, SORT_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH, page
    )


@pytest.mark.slow
def test_sort_user_list_task_from_config(page: Page):
    generic_task_cheat_test(SortUserListTask, SORT_USER_LIST_CONFIG_PATH, page)
