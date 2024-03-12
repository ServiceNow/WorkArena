"""
Tests that are not specific to any particular kind of task.

"""

import json
import logging
import pickle
import pytest

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright

from playwright.sync_api import Page, TimeoutError
from tenacity import retry, stop_after_attempt, retry_if_exception_type

from browsergym.workarena.tasks.form import (
    CreateChangeRequestTask,
    CreateHardwareAssetTask,
    CreateIncidentTask,
    CreateProblemTask,
    CreateUserTask,
)
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

RANDOMLY_CONFIGURALBE_TASKS = [
    CreateChangeRequestTask,
    CreateHardwareAssetTask,
    CreateIncidentTask,
    CreateProblemTask,
    CreateUserTask,
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
    OrderDeveloperLaptopTask,
    OrderIpadMiniTask,
    OrderIpadProTask,
    OrderSalesLaptopTask,
    OrderStandardLaptopTask,
    OrderAppleWatchTask,
    OrderAppleMacBookPro15Task,
    OrderDevelopmentLaptopPCTask,
    OrderLoanerLaptopTask,
]


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint", RANDOMLY_CONFIGURALBE_TASKS)
@pytest.mark.parametrize("random_seed", range(3))
@pytest.mark.slow
def test_cheat_from_random_config(task_entrypoint, random_seed: int, page: Page):
    task = task_entrypoint()
    task._generate_random_config(seed=random_seed, page=page)
    chat_messages = []
    assert task.validate(page, chat_messages)[1] is False
    task.cheat(page=page, chat_messages=chat_messages)
    assert task.validate(page, chat_messages)[1] is True
    task.teardown()
