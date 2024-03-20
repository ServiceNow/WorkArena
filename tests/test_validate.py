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
from browsergym.workarena.config import ORDER_APPLE_WATCH_TASK_CONFIG_PATH

from browsergym.workarena.tasks.service_catalog import OrderAppleWatchTask
from browsergym.workarena.tasks.scripts.validate import validate_configs


@retry(
    stop=stop_after_attempt(2),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
def test_validate_configs(page: Page):
    failed_tasks = validate_configs(
        OrderAppleWatchTask,
        ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
        num_tasks=2,
        save_failed_tasks=False,
        page=page,
    )
    # assert that there are no failed tasks
    assert len(failed_tasks["cheat"]) == 0
    assert len(failed_tasks["no_reward"]) == 0
    assert len(failed_tasks["exception"]) == 0
    assert len(failed_tasks["not_done"]) == 0
